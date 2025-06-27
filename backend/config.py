"""Configuration management following 12-factor app principles."""

from typing import List, Optional

from pydantic_settings import BaseSettings
from pydantic import Field


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    # Application settings
    app_name: str = Field(default="Quorum AI", env="APP_NAME")
    debug: bool = Field(default=False, env="DEBUG")
    host: str = Field(default="0.0.0.0", env="HOST")
    port: int = Field(default=8000, env="PORT")

    # External API settings
    tally_api_base_url: str = Field(
        default="https://api.tally.xyz/query", env="TALLY_API_BASE_URL"
    )
    tally_api_key: Optional[str] = Field(default=None, env="TALLY_API_KEY")

    # AI settings
    openai_api_key: Optional[str] = Field(default=None, env="OPENAI_API_KEY")
    anthropic_api_key: Optional[str] = Field(default=None, env="ANTHROPIC_API_KEY")
    ai_model: str = Field(default="openai:gpt-4o-mini", env="AI_MODEL")

    # Logfire settings
    logfire_token: Optional[str] = Field(default=None, env="LOGFIRE_TOKEN")
    logfire_project: Optional[str] = Field(default=None, env="LOGFIRE_PROJECT")
    logfire_ignore_no_config: bool = Field(
        default=False, env="LOGFIRE_IGNORE_NO_CONFIG"
    )

    # Performance settings
    max_proposals_per_request: int = Field(default=50, env="MAX_PROPOSALS_PER_REQUEST")
    request_timeout: int = Field(default=30, env="REQUEST_TIMEOUT")

    # OpenRouter configuration
    openrouter_api_key: Optional[str] = Field(default=None, env="OPENROUTER_API_KEY")

    # Top organizations configuration
    top_organizations_env: str = Field(
        default="compound,nounsdao,arbitrum", 
        env="TOP_ORGANIZATIONS",
        description="Comma-separated list of top organization slugs"
    )

    @property
    def top_organizations(self) -> List[str]:
        """Parse comma-separated string to list."""
        return [org.strip() for org in self.top_organizations_env.split(',') if org.strip()]

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


# Global settings instance
settings = Settings()
