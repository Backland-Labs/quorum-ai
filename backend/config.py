"""Configuration management following 12-factor app principles."""

import os
from typing import ClassVar, Dict, List, Optional

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
    host: str = "0.0.0.0"
    port: int = 8000

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

    # Top voters endpoint settings
    DEFAULT_TOP_VOTERS_LIMIT: ClassVar[int] = 10
    MAX_TOP_VOTERS_LIMIT: ClassVar[int] = 50
    MIN_TOP_VOTERS_LIMIT: ClassVar[int] = 1
    default_top_voters_limit: int = DEFAULT_TOP_VOTERS_LIMIT
    max_top_voters_limit: int = MAX_TOP_VOTERS_LIMIT
    min_top_voters_limit: int = MIN_TOP_VOTERS_LIMIT

    # Chain configuration
    chain_name: str = "celo"
    celo_rpc: str = Field(
        default="",
        alias="CELO_LEDGER_RPC",
        description="Set from CELO_LEDGER_RPC env var",
    )

    # Safe wallet configuration
    # the safe_addresses come from the pearl runtime env
    # the agent_address comes from The private key is stored in a file called ethereum_private_key.txt in the agent's working directory
    safe_addresses: Dict[str, str] = Field(
        default_factory=dict, description="Parsed from SAFE_CONTRACT_ADDRESSES"
    )
    agent_address: Optional[str] = Field(
        default=None, description="The agent's EOA address"
    )

    # DAO monitoring
    monitored_daos: List[str] = Field(
        default_factory=list,
        alias="MONITORED_DAOS",
        description="From MONITORED_DAOS env var",
    )
    vote_confidence_threshold: float = Field(
        default=0.6, ge=0.0, le=1.0, description="Vote confidence threshold"
    )

    # Activity tracking
    DEFAULT_ACTIVITY_CHECK_INTERVAL_SECONDS: ClassVar[int] = 3600  # 1 hour
    DEFAULT_PROPOSAL_CHECK_INTERVAL_SECONDS: ClassVar[int] = 300  # 5 minutes
    DEFAULT_MIN_TIME_BEFORE_DEADLINE_SECONDS: ClassVar[int] = 1800  # 30 minutes

    activity_check_interval: int = Field(
        default=DEFAULT_ACTIVITY_CHECK_INTERVAL_SECONDS,
        gt=0,
        description="Check every hour",
    )
    proposal_check_interval: int = Field(
        default=DEFAULT_PROPOSAL_CHECK_INTERVAL_SECONDS,
        gt=0,
        description="Check every 5 minutes",
    )
    min_time_before_deadline: int = Field(
        default=DEFAULT_MIN_TIME_BEFORE_DEADLINE_SECONDS,
        gt=0,
        description="30 minutes before 24h deadline",
    )

    # Staking contracts (from Olas env vars)
    staking_token_contract_address: Optional[str] = Field(
        default=None,
        alias="STAKING_TOKEN_CONTRACT_ADDRESS",
        description="Olas staking token contract",
    )
    activity_checker_contract_address: Optional[str] = Field(
        default=None,
        alias="ACTIVITY_CHECKER_CONTRACT_ADDRESS",
        description="Olas activity checker contract",
    )
    service_registry_token_utility_contract: Optional[str] = Field(
        default=None,
        alias="SERVICE_REGISTRY_TOKEN_UTILITY_CONTRACT",
        description="Olas service registry contract",
    )

    # OLAS configuration for new services
    safe_contract_addresses: str = Field(
        default="{}",
        alias="SAFE_CONTRACT_ADDRESSES",
        description="JSON string of Safe addresses by chain",
    )
    store_path: Optional[str] = Field(
        default=None,
        alias="STORE_PATH",
        description="Path for persistent data storage",
    )

    # Agent run configuration
    DEFAULT_MAX_PROPOSALS_PER_RUN: ClassVar[int] = 3
    DEFAULT_DEFAULT_CONFIDENCE_THRESHOLD: ClassVar[float] = 0.7
    DEFAULT_PROPOSAL_FETCH_TIMEOUT: ClassVar[int] = 30
    DEFAULT_VOTE_EXECUTION_TIMEOUT: ClassVar[int] = 60
    DEFAULT_MAX_RETRY_ATTEMPTS: ClassVar[int] = 3
    DEFAULT_RETRY_DELAY_SECONDS: ClassVar[int] = 5

    max_proposals_per_run: int = Field(
        default=DEFAULT_MAX_PROPOSALS_PER_RUN,
        ge=1,
        le=10,
        description="Maximum proposals to process per agent run",
    )
    default_confidence_threshold: float = Field(
        default=DEFAULT_DEFAULT_CONFIDENCE_THRESHOLD,
        ge=0.0,
        le=1.0,
        description="Default confidence threshold for voting decisions",
    )
    proposal_fetch_timeout: int = Field(
        default=DEFAULT_PROPOSAL_FETCH_TIMEOUT,
        gt=0,
        description="Timeout for proposal fetching in seconds",
    )
    vote_execution_timeout: int = Field(
        default=DEFAULT_VOTE_EXECUTION_TIMEOUT,
        gt=0,
        description="Timeout for vote execution in seconds",
    )
    max_retry_attempts: int = Field(
        default=DEFAULT_MAX_RETRY_ATTEMPTS,
        ge=0,
        le=10,
        description="Maximum retry attempts for failed operations",
    )
    retry_delay_seconds: int = Field(
        default=DEFAULT_RETRY_DELAY_SECONDS,
        gt=0,
        description="Delay between retry attempts in seconds",
    )

    # RPC endpoints for multiple chains
    ethereum_ledger_rpc: Optional[str] = Field(
        default=None,
        alias="ETHEREUM_LEDGER_RPC",
        description="Ethereum RPC endpoint",
    )
    gnosis_ledger_rpc: Optional[str] = Field(
        default=None,
        alias="GNOSIS_LEDGER_RPC",
        description="Gnosis chain RPC endpoint",
    )
    base_ledger_rpc: Optional[str] = Field(
        default=None,
        alias="BASE_LEDGER_RPC",
        description="Base chain RPC endpoint",
    )
    mode_ledger_rpc: Optional[str] = Field(
        default=None,
        alias="MODE_LEDGER_RPC",
        description="Mode chain RPC endpoint",
    )

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
        self._parse_safe_addresses()
        self._parse_agent_address()
        self._parse_vote_threshold()
        self._parse_intervals()
        self._parse_agent_run_config()
        return self

    def _parse_safe_addresses(self):
        """Parse safe addresses from SAFE_CONTRACT_ADDRESSES environment variable."""
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

    def _parse_agent_address(self):
        """Parse agent address from AGENT_ADDRESS environment variable."""
        agent_address_env = os.getenv("AGENT_ADDRESS")
        if agent_address_env:
            self.agent_address = agent_address_env

    def _parse_vote_threshold(self):
        """Parse vote confidence threshold from VOTE_CONFIDENCE_THRESHOLD environment variable."""
        vote_threshold_env = os.getenv("VOTE_CONFIDENCE_THRESHOLD")
        if vote_threshold_env:
            threshold = float(vote_threshold_env)
            if not (0.0 <= threshold <= 1.0):
                raise ValueError(
                    f"vote_confidence_threshold must be between 0.0 and 1.0, got {threshold}"
                )
            self.vote_confidence_threshold = threshold

    def _parse_intervals(self):
        """Parse interval settings from environment variables."""
        self._parse_activity_interval()
        self._parse_proposal_interval()
        self._parse_deadline_time()

    def _parse_activity_interval(self):
        """Parse activity check interval from ACTIVITY_CHECK_INTERVAL environment variable."""
        activity_interval_env = os.getenv("ACTIVITY_CHECK_INTERVAL")
        if activity_interval_env:
            interval = int(activity_interval_env)
            if interval <= 0:
                raise ValueError(
                    f"activity_check_interval must be positive, got {interval}"
                )
            self.activity_check_interval = interval

    def _parse_proposal_interval(self):
        """Parse proposal check interval from PROPOSAL_CHECK_INTERVAL environment variable."""
        proposal_interval_env = os.getenv("PROPOSAL_CHECK_INTERVAL")
        if proposal_interval_env:
            interval = int(proposal_interval_env)
            if interval <= 0:
                raise ValueError(
                    f"proposal_check_interval must be positive, got {interval}"
                )
            self.proposal_check_interval = interval

    def _parse_deadline_time(self):
        """Parse minimum time before deadline from MIN_TIME_BEFORE_DEADLINE environment variable."""
        deadline_time_env = os.getenv("MIN_TIME_BEFORE_DEADLINE")
        if deadline_time_env:
            time_val = int(deadline_time_env)
            if time_val <= 0:
                raise ValueError(
                    f"min_time_before_deadline must be positive, got {time_val}"
                )
            self.min_time_before_deadline = time_val

    def _parse_agent_run_config(self):
        """Parse agent run configuration from environment variables."""
        self._parse_max_proposals_per_run()
        self._parse_default_confidence_threshold()
        self._parse_proposal_fetch_timeout()
        self._parse_vote_execution_timeout()
        self._parse_max_retry_attempts()
        self._parse_retry_delay_seconds()

    def _parse_max_proposals_per_run(self):
        """Parse max proposals per run from MAX_PROPOSALS_PER_RUN environment variable."""
        max_proposals_env = os.getenv("MAX_PROPOSALS_PER_RUN")
        if max_proposals_env:
            max_proposals = int(max_proposals_env)
            if not (1 <= max_proposals <= 10):
                raise ValueError(
                    f"max_proposals_per_run must be between 1 and 10, got {max_proposals}"
                )
            self.max_proposals_per_run = max_proposals

    def _parse_default_confidence_threshold(self):
        """Parse default confidence threshold from DEFAULT_CONFIDENCE_THRESHOLD environment variable."""
        confidence_threshold_env = os.getenv("DEFAULT_CONFIDENCE_THRESHOLD")
        if confidence_threshold_env:
            threshold = float(confidence_threshold_env)
            if not (0.0 <= threshold <= 1.0):
                raise ValueError(
                    f"default_confidence_threshold must be between 0.0 and 1.0, got {threshold}"
                )
            self.default_confidence_threshold = threshold

    def _parse_proposal_fetch_timeout(self):
        """Parse proposal fetch timeout from PROPOSAL_FETCH_TIMEOUT environment variable."""
        timeout_env = os.getenv("PROPOSAL_FETCH_TIMEOUT")
        if timeout_env:
            timeout = int(timeout_env)
            if timeout <= 0:
                raise ValueError(
                    f"proposal_fetch_timeout must be positive, got {timeout}"
                )
            self.proposal_fetch_timeout = timeout

    def _parse_vote_execution_timeout(self):
        """Parse vote execution timeout from VOTE_EXECUTION_TIMEOUT environment variable."""
        timeout_env = os.getenv("VOTE_EXECUTION_TIMEOUT")
        if timeout_env:
            timeout = int(timeout_env)
            if timeout <= 0:
                raise ValueError(
                    f"vote_execution_timeout must be positive, got {timeout}"
                )
            self.vote_execution_timeout = timeout

    def _parse_max_retry_attempts(self):
        """Parse max retry attempts from MAX_RETRY_ATTEMPTS environment variable."""
        max_retry_env = os.getenv("MAX_RETRY_ATTEMPTS")
        if max_retry_env:
            max_retry = int(max_retry_env)
            if not (0 <= max_retry <= 10):
                raise ValueError(
                    f"max_retry_attempts must be between 0 and 10, got {max_retry}"
                )
            self.max_retry_attempts = max_retry

    def _parse_retry_delay_seconds(self):
        """Parse retry delay seconds from RETRY_DELAY_SECONDS environment variable."""
        delay_env = os.getenv("RETRY_DELAY_SECONDS")
        if delay_env:
            delay = int(delay_env)
            if delay <= 0:
                raise ValueError(f"retry_delay_seconds must be positive, got {delay}")
            self.retry_delay_seconds = delay

    @property
    def monitored_daos_list(self) -> List[str]:
        """Parse comma-separated DAO list from environment."""
        daos_env = os.getenv("MONITORED_DAOS", "")
        default_monitored_daos = "compound.eth,nouns.eth,arbitrum.eth"
        if not daos_env.strip():
            # Fall back to default when empty
            daos_env = default_monitored_daos
        return [dao.strip() for dao in daos_env.split(",") if dao.strip()]

    @property
    def safe_addresses_dict(self) -> Dict[str, str]:
        """Parse safe addresses from environment variable."""
        safe_addresses_env = os.getenv("SAFE_CONTRACT_ADDRESSES", "")
        if not safe_addresses_env:
            return {}

        addresses = {}
        for pair in safe_addresses_env.split(","):
            if ":" in pair:
                dao, address = pair.split(":", 1)
                dao = dao.strip()
                address = address.strip()
                if dao and address:
                    addresses[dao] = address
        return addresses

    def reload_config(self) -> None:
        """Reload configuration from environment variables.

        This method allows hot-reloading of configuration without restarting
        the application. It re-parses all environment variables and updates
        the configuration values.
        """
        # Re-parse all environment-specific settings
        self.parse_env_settings()

        # Re-validate the configuration after reloading
        self.model_validate(self.model_dump())

    def get_agent_run_config(self) -> Dict[str, any]:
        """Get agent run configuration as a dictionary.

        Returns:
            Dict containing all agent run configuration values.
        """
        return {
            "max_proposals_per_run": self.max_proposals_per_run,
            "default_confidence_threshold": self.default_confidence_threshold,
            "proposal_fetch_timeout": self.proposal_fetch_timeout,
            "vote_execution_timeout": self.vote_execution_timeout,
            "max_retry_attempts": self.max_retry_attempts,
            "retry_delay_seconds": self.retry_delay_seconds,
        }


# Global settings instance
settings = Settings()
