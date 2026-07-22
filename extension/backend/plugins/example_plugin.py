import logging

logger = logging.getLogger("capsule.plugins.example")

async def pre_analyze_pr(pr_number: int, repo: str, title: str):
    """
    Example hook called before a PR is analyzed.
    """
    logger.info(f"[Plugin: Example] Starting analysis for PR #{pr_number} in {repo} - '{title}'")

async def post_analyze_pr(pr_number: int, repo: str, quality_score: int):
    """
    Example hook called after a PR is analyzed.
    """
    logger.info(f"[Plugin: Example] Completed analysis for PR #{pr_number} in {repo}. Quality Score: {quality_score}")
