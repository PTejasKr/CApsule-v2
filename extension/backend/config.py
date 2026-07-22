import os
from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field

class Settings(BaseSettings):
    API_KEY: str = Field("test_api_key_placeholder", description="API key used to authenticate requests from Chrome Extension")

    GITHUB_TOKEN: str = Field("test_github_token_placeholder", description="GitHub Personal Access Token with repo scope")
    GITHUB_WEBHOOK_SECRET: str = Field("test_github_webhook_secret_placeholder", description="Secret for validating webhook HMAC signatures")
    CHANGELOG_REPO: str = Field("", description="Separate repository name (owner/repo) where changelog.txt is pushed")
    GITHUB_CLIENT_ID: str = Field("", description="GitHub OAuth App Client ID")
    GITHUB_CLIENT_SECRET: str = Field("", description="GitHub OAuth App Client Secret")
    COMPANY_GITHUB_ORG: str = Field("", description="Authorized GitHub Organization for Extension Auto-Login")
    HOST_URL: str = Field("http://localhost:8000", description="Backend host URL for OAuth redirects")

    NVIDIA_NIM_API_KEY: str = Field("test_nvidia_nim_api_key_placeholder", description="NVIDIA NIM API key")
    NVIDIA_NIM_BASE_URL: str = Field("https://integrate.api.nvidia.com/v1", description="NVIDIA NIM base API URL")
    NVIDIA_NIM_MODEL: str = Field("meta/llama-3.1-70b-instruct", description="LLM model name to use on NVIDIA NIM")

    GEMINI_API_KEY: str = Field("", description="Google Gemini API key")
    GROQ_API_KEY: str = Field("", description="Groq API key")
    OPENROUTER_API_KEY: str = Field("", description="OpenRouter API key")
    OLLAMA_BASE_URL: str = Field("http://localhost:11434/v1", description="Local Ollama base URL")

    JENKINS_API_TOKEN: str = Field("", description="Jenkins API token for triggering pipelines")

    BRD_FILE_PATH: str = Field("./brd/requirements.md", description="Path to the Business Requirement Document")
    DATABASE_URL: str = Field("sqlite+aiosqlite:///./data/capsule.db", description="Database connection URL")
    LOG_LEVEL: str = Field("INFO", description="Log level (DEBUG, INFO, WARNING, ERROR)")
    CLOUDFLARE_WORKER_URL: str = Field("http://localhost:8787", description="Cloudflare Worker URL for image generation and summaries")
    GLOBAL_REDUCE_ENABLED: bool = Field(True, description="Run a holistic LLM reduce pass over merged chunks to capture cross-file relationships")

    ENCRYPTION_KEY: str = Field("test_encryption_key_must_be_32_bytes_or_more!", description="Key for encrypting tokens at rest")
    DATA_RETENTION_DAYS: int = Field(30, description="Days to retain audit logs and PR analyses before deletion")

    SLACK_WEBHOOK_URL: str = Field("", description="Incoming webhook URL for Slack notifications")
    TEAMS_WEBHOOK_URL: str = Field("", description="Incoming webhook URL for Microsoft Teams notifications")
    TRELLO_API_KEY: str = Field("", description="Trello API Key for issue creation")
    TRELLO_TOKEN: str = Field("", description="Trello API Token for issue creation")
    TRELLO_LIST_ID: str = Field("", description="Trello List ID where issues will be created")

    model_config = SettingsConfigDict(
        env_file=os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), ".env"),
        env_file_encoding="utf-8",
        extra="ignore"
    )

settings = Settings()

for field_name in settings.model_fields:
    val = getattr(settings, field_name)
    if isinstance(val, str):
        setattr(settings, field_name, val.lstrip("\ufeff").strip())

