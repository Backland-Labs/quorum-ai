"""Configuration management following 12-factor app principles."""

import os
from typing import Dict, List, Optional

from pydantic import Field, field_validator, model_validator
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    model_config = {
        "env_file": ".env", 
        "extra": "ignore",
        "env_parse_none_str": "None",
        "env_nested_delimiter": "__",
    }

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

    # DAO monitoring
    monitored_daos: List[str] = Field(default_factory=list, alias="MONITORED_DAOS", description="From MONITORED_DAOS env var")
    vote_confidence_threshold: float = Field(default=0.6, ge=0.0, le=1.0, description="Vote confidence threshold")

    # Activity tracking
    activity_check_interval: int = Field(default=3600, gt=0, description="Check every hour")
    proposal_check_interval: int = Field(default=300, gt=0, description="Check every 5 minutes")
    min_time_before_deadline: int = Field(default=1800, gt=0, description="30 minutes before 24h deadline")

    # Staking contracts (from Olas env vars)
    staking_token_contract_address: Optional[str] = Field(default=None, alias="STAKING_TOKEN_CONTRACT_ADDRESS", description="Olas staking token contract")
    activity_checker_contract_address: Optional[str] = Field(default=None, alias="ACTIVITY_CHECKER_CONTRACT_ADDRESS", description="Olas activity checker contract")
    service_registry_token_utility_contract: Optional[str] = Field(default=None, alias="SERVICE_REGISTRY_TOKEN_UTILITY_CONTRACT", description="Olas service registry contract")

    @field_validator("monitored_daos", mode="before")
    @classmethod
    def parse_monitored_daos(cls, v):
        """Parse monitored DAOs from comma-separated string."""
        if isinstance(v, str):
            if not v.strip():
                return []
            return [dao.strip() for dao in v.split(",") if dao.strip()]
        elif isinstance(v, list):
            return v
        return v or []

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
        
        # Parse vote confidence threshold from environment variable
        vote_threshold_env = os.getenv("VOTE_CONFIDENCE_THRESHOLD")
        if vote_threshold_env:
            threshold = float(vote_threshold_env)
            if not (0.0 <= threshold <= 1.0):
                raise ValueError(f"vote_confidence_threshold must be between 0.0 and 1.0, got {threshold}")
            self.vote_confidence_threshold = threshold
        
        # Parse activity intervals from environment variables
        activity_interval_env = os.getenv("ACTIVITY_CHECK_INTERVAL")
        if activity_interval_env:
            interval = int(activity_interval_env)
            if interval <= 0:
                raise ValueError(f"activity_check_interval must be positive, got {interval}")
            self.activity_check_interval = interval
        
        proposal_interval_env = os.getenv("PROPOSAL_CHECK_INTERVAL")
        if proposal_interval_env:
            interval = int(proposal_interval_env)
            if interval <= 0:
                raise ValueError(f"proposal_check_interval must be positive, got {interval}")
            self.proposal_check_interval = interval
        
        deadline_time_env = os.getenv("MIN_TIME_BEFORE_DEADLINE")
        if deadline_time_env:
            time_val = int(deadline_time_env)
            if time_val <= 0:
                raise ValueError(f"min_time_before_deadline must be positive, got {time_val}")
            self.min_time_before_deadline = time_val
            
        return self

    @property
    def top_organizations(self) -> List[str]:
        """Parse comma-separated string to list."""
        return [
            org.strip() for org in self.top_organizations_env.split(",") if org.strip()
        ]


# Global settings instance
settings = Settings()
