import logging
import httpx
from extension.backend.config import settings

logger = logging.getLogger("capsule.integrations")

class ChatOpsService:
    @staticmethod
    async def notify_pr_analysis(pr_number: int, repo: str, title: str, quality_score: int, workflow_severity: str):
        """
        Sends a notification to Slack and/or Teams if their webhooks are configured.
        """
        message = f"Capsule PR Analysis complete for #{pr_number} in {repo} ('{title}').\nQuality Score: {quality_score}/100\nWorkflow Impact: {workflow_severity.upper()}"
        
        # Slack
        if getattr(settings, "SLACK_WEBHOOK_URL", ""):
            payload = {"text": message}
            try:
                async with httpx.AsyncClient() as client:
                    await client.post(settings.SLACK_WEBHOOK_URL, json=payload)
            except Exception as e:
                logger.error(f"Failed to send Slack notification: {e}")
                
        # MS Teams
        if getattr(settings, "TEAMS_WEBHOOK_URL", ""):
            payload = {"text": message}
            try:
                async with httpx.AsyncClient() as client:
                    await client.post(settings.TEAMS_WEBHOOK_URL, json=payload)
            except Exception as e:
                logger.error(f"Failed to send Teams notification: {e}")

class IssueTrackerService:
    @staticmethod
    async def create_violation_ticket(pr_number: int, repo: str, title: str, changes_summary: str):
        """
        Creates a ticket in Trello (as a generic free issue tracker) for major violations.
        """
        api_key = getattr(settings, "TRELLO_API_KEY", "")
        token = getattr(settings, "TRELLO_TOKEN", "")
        list_id = getattr(settings, "TRELLO_LIST_ID", "")
        
        if not (api_key and token and list_id):
            return # Not configured
            
        name = f"Major Violation in PR #{pr_number}: {repo}"
        desc = f"PR Title: {title}\n\nThe following PR has severe violations and needs review:\n\n{changes_summary}"
        
        try:
            async with httpx.AsyncClient() as client:
                res = await client.post(
                    "https://api.trello.com/1/cards",
                    params={
                        "key": api_key,
                        "token": token,
                        "idList": list_id,
                        "name": name,
                        "desc": desc
                    }
                )
                if res.status_code != 200:
                    logger.error(f"Failed to create Trello card. Status {res.status_code}: {res.text}")
        except Exception as e:
            logger.error(f"Error creating Trello ticket: {e}")
