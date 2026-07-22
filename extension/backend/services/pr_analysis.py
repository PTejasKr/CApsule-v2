import json
import logging
from extension.backend.services.ai_engine import AIEngine
from typing import Optional
from extension.backend.models.schemas import PRSummary
from extension.backend.database import insert
from extension.backend.services.github_service import GitHubService
from extension.backend.services.brd_manager import BRDManager

ai_engine = AIEngine()

logger = logging.getLogger("capsule.pr_analysis")

github_service = GitHubService()
brd_manager = BRDManager()

async def run_pr_analysis(
    repo: str,
    pr_number: int,
    branch_name: Optional[str] = None,
    github_service=None,
    ai_engine=None,
    brd_manager=None,
) -> dict:
    """Fetch PR details, run AI analysis, persist the result.

    Args:
        repo: Repository identifier in "owner/repo" format.
        pr_number: Pull request number.
        branch_name: Optional branch name; if omitted it will be derived from the PR data.
        github_service: Optional custom GitHubService instance (for mocking in tests).
        ai_engine: Optional custom AIEngine instance (for mocking in tests).
        brd_manager: Optional custom BRDManager instance (for mocking in tests).

    Returns:
        The dictionary representation of the persisted PRSummary.
    """
    gh = github_service if github_service is not None else globals()["github_service"]
    ai = ai_engine if ai_engine is not None else globals()["ai_engine"]
    brd_mngr = brd_manager if brd_manager is not None else globals()["brd_manager"]

    pr_details = await gh.get_pr_details(repo, pr_number)
    title = pr_details.get("title", "")
    head_sha = pr_details.get("head_sha", "")
    
    if head_sha:
        try:
            await gh.create_status_check(
                repo=repo,
                sha=head_sha,
                state="pending",
                description="Capsule AI is analyzing the changes..."
            )
        except Exception as e:
            logger.warning(f"Could not set pending status check: {e}")

    diff = await gh.get_pr_diff(repo, pr_number)
    
    if branch_name is None:
        branch_name = pr_details.get("head_ref", "")

    brd_content = await brd_mngr.load_brd(1)

    from extension.backend.database import fetch_one
    profile_row = await fetch_one("SELECT custom_rules FROM profiles WHERE id = 1")
    custom_rules = profile_row.get("custom_rules") if profile_row else None

    summary: PRSummary = await ai.analyze_pr(
        pr_number=pr_number,
        repo=repo,
        pr_title=title,
        diff=diff,
        brd_content=brd_content,
        branch_name=branch_name,
        custom_rules=custom_rules,
    )

    if head_sha:
        # Determine status based on confidence score (e.g., threshold of 0.7)
        # Note: Depending on rules, you could also check for critical severity issues.
        state = "success" if summary.confidence_score >= 0.7 else "failure"
        description = f"Analysis complete. Confidence: {summary.confidence_score:.2f}"
        try:
            await gh.create_status_check(
                repo=repo,
                sha=head_sha,
                state=state,
                description=description
            )
        except Exception as e:
            logger.warning(f"Could not set final status check: {e}")

    try:
        db_data = {
            "pr_number": pr_number,
            "repo": repo,
            "title": summary.title,
            "summary": summary.summary,
            "original_summary": summary.summary,
            "brd_comparison": summary.brd_comparison,
            "branch": branch_name or summary.branch,
            "approved": False,
            "changes_json": json.dumps([c.model_dump() for c in summary.changes]),
            "workflow_impact_json": json.dumps(summary.workflow_impact.model_dump()),
            "confidence_score": summary.confidence_score,
            "author": pr_details.get("user", ""),
            "merged_at": pr_details.get("merged_at", "")
        }
        record_id = await insert("pr_analyses", db_data)
        logger.info(f"PR analysis persisted with id {record_id}")
    except Exception as e:
        logger.error(f"Failed to insert PR analysis result: {e}")
        raise

    result = summary.model_dump()
    result["id"] = record_id
    
    # Post PR comment with summary
    try:
        comment_body = f"## 💊 Capsule AI PR Analysis\n\n**Summary:**\n{summary.summary}\n\n"
        
        if summary.workflow_impact.has_impact:
            severity = summary.workflow_impact.severity.value if hasattr(summary.workflow_impact.severity, 'value') else summary.workflow_impact.severity
            comment_body += f"### ⚠️ Workflow Impact ({severity})\n{summary.workflow_impact.impact_description}\n\n"
            
        if summary.changes:
            comment_body += "### 📝 Technical Changes\n"
            for c in summary.changes:
                ctype = c.change_type.value if hasattr(c.change_type, 'value') else c.change_type
                comment_body += f"- **`{c.file}`** ({ctype}): {c.description}\n"
                
        await gh.post_pr_comment(repo=repo, pr_number=pr_number, body=comment_body)
        logger.info(f"Successfully posted PR comment for #{pr_number}")
    except Exception as e:
        logger.error(f"Failed to post PR comment for #{pr_number}: {e}")

    return result

