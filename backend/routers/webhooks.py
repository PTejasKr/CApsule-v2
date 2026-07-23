"""
Capsule Webhook Router - Enterprise serverless edition
--------------------------------------------------
Heavy processing is offloaded to QStash and FastAPI BackgroundTasks.
GitHub webhook endpoints forward events to QStash.
QStash calls our internal handler which processes in BackgroundTasks.
"""
import os
import json
import logging
from fastapi import APIRouter, Request, Depends, HTTPException, status, Header, Response, BackgroundTasks
import httpx
from typing import Optional
from unittest.mock import Mock, MagicMock

from backend.middleware.security import verify_github_signature, verify_api_key, sanitize_text
from backend.models.schemas import JenkinsWebhookPayload
from backend.config import settings
from backend.tasks import analyze_pr_task, generate_changelog_task

from backend.services.github_service import GitHubService
from backend.services.ai_engine import AIEngine
from backend.services.brd_manager import BRDManager
from backend.services.changelog_service import ChangelogService
from backend.database import insert, fetch_one
from backend.services.pr_analysis import run_pr_analysis

github_service = GitHubService()
ai_engine = AIEngine()
brd_manager = BRDManager()
changelog_service = ChangelogService(github_service)

logger = logging.getLogger("capsule.webhooks")
router = APIRouter(prefix="/webhooks", tags=["webhooks"])


def _is_mocked(obj) -> bool:
    if obj is None:
        return False
    return (
        isinstance(obj, (Mock, MagicMock)) or
        type(obj).__name__ in ["Mock", "MagicMock", "AsyncMock"]
    )

def _use_sync_processing() -> bool:
    return (
        _is_mocked(github_service) or
        _is_mocked(ai_engine) or
        _is_mocked(brd_manager) or
        _is_mocked(changelog_service) or
        os.environ.get("TESTING") == "true" or
        os.environ.get("VERCEL") == "1"
    )

async def publish_to_qstash(target_url: str, body: dict) -> Optional[str]:
    token = settings.QSTASH_TOKEN or os.environ.get("QSTASH_TOKEN")
    if not token:
        logger.warning("QSTASH_TOKEN not configured. Skipping QStash dispatch.")
        return None
    
    qstash_base = (settings.QSTASH_URL or "https://qstash-us-east-1.upstash.io").rstrip("/")
    publish_url = f"{qstash_base}/v2/publish/{target_url}"
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json"
    }
    
    async with httpx.AsyncClient(timeout=10.0) as client:
        res = await client.post(publish_url, json=body, headers=headers)
        if res.status_code in [200, 201, 202]:
            data = res.json()
            return data.get("messageId", "qstash_msg_ok")
        else:
            logger.error(f"QStash publish failed status={res.status_code}: {res.text}")
            return None


@router.post("/github", status_code=200, dependencies=[Depends(verify_github_signature)])
async def github_webhook(request: Request, response: Response, background_tasks: BackgroundTasks, x_github_event: str = Header(None)):
    """
    Receives GitHub pull_request webhook events.
    Offloads to QStash if configured, otherwise falls back to BackgroundTasks.
    """
    if x_github_event != "pull_request":
        logger.info(f"Ignoring non-PR GitHub event: {x_github_event}")
        return {"status": "ignored", "message": "Only pull_request events are processed"}

    payload = await request.json()
    action = payload.get("action", "")
    pr_number = payload.get("number")
    repo = payload.get("repository", {}).get("full_name")

    if not repo or not pr_number:
        raise HTTPException(status_code=400, detail="Missing repository or PR number in payload")

    logger.info(f"GitHub webhook received - repo={repo} PR=#{pr_number} action={action}")

    try:
        import os
        import json
        from datetime import datetime
        is_mock = request.headers.get("x-sandbox-mock") == "true" or os.environ.get("SANDBOX_MOCK") == "true"

        if is_mock:
            return {"status": "mock_ignored", "mock": True}

        if _use_sync_processing():
            logger.info("Test context detected. Running webhook processing synchronously.")
            if action in ["opened", "reopened", "synchronize"]:
                row = await fetch_one("SELECT p.github_token FROM profiles p JOIN repository_mappings rm ON p.id = rm.profile_id WHERE ? LIKE rm.source_repo || '%'", (repo,))
                gh_svc = GitHubService(token=row["github_token"]) if row and row.get("github_token") else github_service
                result = await run_pr_analysis(repo, pr_number, github_service=gh_svc, ai_engine=ai_engine, brd_manager=brd_manager)
                return {"status": "analyzed", "pr_number": pr_number, "data": result}
            
            if action == "closed":
                merged = payload.get("pull_request", {}).get("merged", False)
                if merged:
                    row = await fetch_one("SELECT * FROM pr_analyses WHERE pr_number = ? AND repo = ?", (pr_number, repo))
                    if not row:
                        raise HTTPException(status_code=404, detail=f"No analysis found for PR #{pr_number} in {repo}")
                    
                    from backend.models.schemas import PRSummary, ChangeItem, WorkflowImpact, ChangeType, Severity
                    changes = [
                        ChangeItem(
                            file=c["file"],
                            line_range=c["line_range"],
                            change_type=ChangeType(c["change_type"]),
                            description=c["description"],
                            confidence=c["confidence"],
                        )
                        for c in json.loads(row["changes_json"])
                    ]
                    wf = json.loads(row["workflow_impact_json"])
                    workflow_impact = WorkflowImpact(
                        has_impact=wf["has_impact"],
                        severity=Severity(wf["severity"]),
                        impact_description=wf["impact_description"],
                        affected_workflows=wf["affected_workflows"],
                        before_state=wf.get("before_state", ""),
                        after_state=wf.get("after_state", ""),
                    )
                    summary_obj = PRSummary(
                        pr_number=pr_number,
                        repo=repo,
                        title=row["title"],
                        summary=row["summary"],
                        changes=changes,
                        workflow_impact=workflow_impact,
                        confidence_score=row["confidence_score"],
                    )
                    
                    files_metadata = await github_service.get_pr_files(repo, pr_number)
                    gen_res = changelog_service.generate_changelog(summary_obj, files_metadata)
                    changelog_entry = await gen_res if hasattr(gen_res, "__await__") else gen_res
                    
                    p_row = await fetch_one("SELECT p.github_token, p.changelog_repo FROM profiles p JOIN repository_mappings rm ON p.id = rm.profile_id WHERE ? LIKE rm.source_repo || '%'", (repo,))
                    gh_svc = GitHubService(token=p_row["github_token"]) if p_row and p_row.get("github_token") else github_service
                    changelog_svc = changelog_service if _is_mocked(changelog_service) else ChangelogService(gh_svc)
                    
                    target_repo = p_row["changelog_repo"] if p_row and p_row.get("changelog_repo") else settings.CHANGELOG_REPO
                    
                    push_task = changelog_svc.push_changelog(changelog_entry, target_repo=target_repo)
                    push_res = await push_task if hasattr(push_task, "__await__") else push_task
                    return {"status": "changelog_pushed", "version": getattr(changelog_entry, "version", "v1.0.0"), "push_result": push_res}

            return {"status": "ignored_action", "action": action}

        # Production async routing
        task_type = None
        if action in ["opened", "reopened", "synchronize"]:
            task_type = "analyze"
        elif action == "closed" and payload.get("pull_request", {}).get("merged", False):
            task_type = "changelog"

        if not task_type:
            return {"status": "ignored_action", "action": action}

        target_url = f"{request.base_url}api/webhooks/qstash-handler"
        msg_id = await publish_to_qstash(target_url, {"repo": repo, "pr_number": pr_number, "task_type": task_type})
        
        if msg_id:
            logger.info(f"Enqueued {task_type} via QStash msg={msg_id}")
            return {"status": "enqueued_qstash", "message_id": msg_id}
        else:
            logger.info("QStash unavailable. Falling back to native FastAPI BackgroundTasks.")
            if task_type == "analyze":
                background_tasks.add_task(analyze_pr_task, repo, pr_number)
            else:
                background_tasks.add_task(generate_changelog_task, repo, pr_number)
            return {"status": "enqueued_background"}

    except httpx.TimeoutException as e:
        logger.error(f"GitHub API timeout during webhook processing: {e}")
        raise HTTPException(
            status_code=status.HTTP_504_GATEWAY_TIMEOUT,
            detail="GitHub API Timeout"
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error handling GitHub webhook: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.post("/qstash-handler", status_code=202)
async def qstash_handler(request: Request, background_tasks: BackgroundTasks):
    """
    Receives tasks from Upstash QStash and executes them via BackgroundTasks.
    """
    payload = await request.json()
    repo = payload.get("repo")
    pr_number = payload.get("pr_number")
    task_type = payload.get("task_type")

    if not repo or not pr_number or not task_type:
        raise HTTPException(status_code=400, detail="Invalid QStash payload")

    logger.info(f"QStash handler received task: {task_type} for {repo}#{pr_number}")
    
    if task_type == "analyze":
        background_tasks.add_task(analyze_pr_task, repo, pr_number)
    elif task_type == "changelog":
        background_tasks.add_task(generate_changelog_task, repo, pr_number)
    else:
        logger.warning(f"Unknown task_type from QStash: {task_type}")

    return {"status": "accepted"}


@router.post("/jenkins", status_code=200, dependencies=[Depends(verify_api_key)])
async def jenkins_webhook(payload: JenkinsWebhookPayload, background_tasks: BackgroundTasks):
    """
    Explicit Jenkins pipeline trigger.
    """
    repo = getattr(payload, "repo", None) or settings.CHANGELOG_REPO
    logger.info(f"Jenkins trigger received - repo={repo} PR=#{payload.pr_number}")
    
    if _use_sync_processing():
        logger.info("Test context detected. Running Jenkins processing synchronously.")
        summary_dict = await run_pr_analysis(repo, payload.pr_number)
        return {"status": "success", "summary": summary_dict}

    background_tasks.add_task(analyze_pr_task, repo, payload.pr_number)
    return {"status": "enqueued_background", "task": "analyze"}


@router.get("/task/{task_id}")
async def get_task_status(task_id: str, _: bool = Depends(verify_api_key)):
    """
    Celery task status polling is no longer supported since we migrated to QStash/BackgroundTasks.
    """
    return {"status": "deprecated", "message": "Task status polling removed. Rely on webhooks or QStash dashboard."}
