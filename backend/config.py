"""Configuration management following 12-factor app principles."""

from typing import List, Optional

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    model_config = {"env_file": ".env", "extra": "ignore"}

    # Application settings
    app_name: str = "Quorum AI"
    debug: bool = False
    host: str = "0.0.0.0"
    port: int = 8000

    # External API settings
    tally_api_base_url: str = "https://api.tally.xyz/query"
    tally_api_key: Optional[str] = None

    # AI settings
    openai_api_key: Optional[str] = None
    anthropic_api_key: Optional[str] = None
    ai_model: str = "openai:gpt-4o-mini"

    # Logfire settings
    logfire_token: Optional[str] = None
    logfire_project: Optional[str] = None
    logfire_ignore_no_config: bool = False

    # Performance settings
    max_proposals_per_request: int = 50
    request_timeout: int = 30
    
    # Redis settings
    redis_url: str = "redis://localhost:6379/0"
    redis_password: Optional[str] = None
    redis_max_connections: int = 50
    redis_decode_responses: bool = True
    redis_socket_connect_timeout: int = 10
    redis_socket_keepalive: bool = True
    redis_health_check_interval: int = 30

    # OpenRouter configuration
    openrouter_api_key: Optional[str] = None

    # Top organizations configuration
    top_organizations_env: str = "compound,nounsdao,arbitrum"

    @property
    def top_organizations(self) -> List[str]:
        """Parse comma-separated string to list."""
        return [
            org.strip() for org in self.top_organizations_env.split(",") if org.strip()
        ]
    
    @property
    def redis_connection_url(self) -> str:
        """Build Redis connection URL with password if provided."""
        if self.redis_password:
            # Parse the URL and insert password
            from urllib.parse import urlparse, urlunparse
            parsed = urlparse(self.redis_url)
            # Create new netloc with password
            netloc = f":{self.redis_password}@{parsed.hostname}"
            if parsed.port:
                netloc += f":{parsed.port}"
            return urlunparse((
                parsed.scheme,
                netloc,
                parsed.path,
                parsed.params,
                parsed.query,
                parsed.fragment
            ))
        return self.redis_url


# Global settings instance
settings = Settings()
