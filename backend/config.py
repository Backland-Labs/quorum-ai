"""Configuration management following 12-factor app principles."""

import os
from typing import Dict, List, Optional

from pydantic import Field, field_validator, model_validator
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    model_config = {"env_file": ".env", "extra": "ignore"}

    # Application settings
    app_name: str = "Quorum AI"
    debug: bool = False

    # External API settings
    tally_api_base_url: str = "https://api.tally.xyz/query"
    tally_api_key: Optional[str] = None

    # AI settings
    anthropic_api_key: Optional[str] = None
    ai_model: str = "openai:gpt-4o-mini"

    # Logfire settings
    logfire_token: Optional[str] = None
    logfire_project: Optional[str] = None
    logfire_ignore_no_config: bool = False

    # Performance settings
    request_timeout: int = 30

    # OpenRouter configuration
    openrouter_api_key: Optional[str] = None

    # Top organizations configuration
    top_organizations_env: str = "compound,nounsdao,arbitrum"

    # Top voters endpoint settings
    default_top_voters_limit: int = 10
    max_top_voters_limit: int = 50
    min_top_voters_limit: int = 1

    # Chain configuration
    chain_name: str = "celo"
    celo_rpc: str = Field(default="", alias="CELO_LEDGER_RPC", description="Set from CELO_LEDGER_RPC env var")

    # Safe wallet configuration
    safe_addresses: Dict[str, str] = Field(default_factory=dict, description="Parsed from SAFE_CONTRACT_ADDRESSES")
    agent_address: Optional[str] = Field(default=None, description="The agent's EOA address")

    @model_validator(mode="after")
    def parse_env_settings(self):
        """Parse environment-specific settings after model initialization."""
        # Parse safe addresses from environment variable
        safe_addresses_env = os.getenv("SAFE_CONTRACT_ADDRESSES", "")
        if safe_addresses_env:
            addresses = {}
            for pair in safe_addresses_env.split(","):
                if ":" in pair:
                    dao, address = pair.split(":", 1)
                    dao = dao.strip()
                    address = address.strip()
                    if dao and address:
                        addresses[dao] = address
            self.safe_addresses = addresses
        
        # Parse agent address from environment variable
        agent_address_env = os.getenv("AGENT_ADDRESS")
        if agent_address_env:
            self.agent_address = agent_address_env
            
        return self

    @property
    def top_organizations(self) -> List[str]:
        """Parse comma-separated string to list."""
        return [
            org.strip() for org in self.top_organizations_env.split(",") if org.strip()
        ]


# Global settings instance
settings = Settings()
