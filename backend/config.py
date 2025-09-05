"""Configuration management following 12-factor app principles."""

import os
from typing import ClassVar, Dict, List, Optional

from pydantic import Field, field_validator, model_validator
from pydantic_settings import BaseSettings
from web3 import Web3

from utils.env_helper import get_env_with_prefix


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    model_config = {
        "env_file": [".env", "../.env"],  # Check both backend/.env and parent .env
        "extra": "ignore",
        "env_parse_none_str": "None",
        "env_nested_delimiter": "__",
    }

    # Pearl logging constants
    VALID_LOG_LEVELS: ClassVar[List[str]] = ["DEBUG", "INFO", "WARNING", "ERROR"]
    DEFAULT_LOG_LEVEL: ClassVar[str] = "INFO"
    DEFAULT_LOG_FILE_PATH: ClassVar[str] = "log.txt"

    # Health check constants
    HEALTH_CHECK_TIMEOUT: int = Field(
        default=50,
        ge=1,
        alias="HEALTH_CHECK_TIMEOUT",
        description="Health check timeout in milliseconds for Pearl compliance",
    )
    HEALTH_CHECK_ENABLED: bool = Field(
        default=True,
        alias="HEALTH_CHECK_ENABLED",
        description="Enable health check functionality for Pearl compliance",
    )
    PEARL_LOG_FORMAT: str = Field(
        default="[%Y-%m-%d %H:%M:%S,%f] [%levelname] [agent] %message",
        alias="PEARL_LOG_FORMAT",
        description="Pearl-compliant log format string",
    )

    # Application settings
    app_name: str = "Quorum AI"
    debug: bool = False
    host: str = "0.0.0.0"
    port: int = 8716

    # AI settings
    ai_model: str = "google/gemini-2.0-flash-001"

    # Pearl logging settings
    log_level: str = Field(
        default=DEFAULT_LOG_LEVEL,
        alias="LOG_LEVEL",
        description="Pearl-compliant log level (DEBUG, INFO, WARNING, ERROR)",
    )
    log_file_path: str = Field(
        default=DEFAULT_LOG_FILE_PATH,
        alias="LOG_FILE_PATH",
        description="Path to Pearl-compliant log file",
    )

    # Performance settings
    request_timeout: int = 30

    # OpenRouter configuration
    openrouter_api_key: Optional[str] = None

    # Snapshot API configuration
    snapshot_graphql_endpoint: str = Field(
        default="https://hub.snapshot.org/graphql",
        alias="SNAPSHOT_GRAPHQL_ENDPOINT",
        description="Snapshot GraphQL API endpoint",
    )

    # Olas-specific configuration fields
    snapshot_api_key: Optional[str] = Field(
        default=None, description="Snapshot API key for enhanced rate limits"
    )
    voting_strategy: str = Field(
        default="balanced",
        description="Voting strategy: balanced, conservative, or aggressive",
    )
    dao_addresses: List[str] = Field(
        default_factory=list, description="List of DAO addresses to monitor"
    )

    rpc_url: str = Field(
        default="http://localhost:8545",
        alias="RPC_URL",
        description="RPC URL for blockchain connection",
    )
    chain_id: int = Field(
        default=8453,
        alias="CHAIN_ID",
        description="Chain ID for the network (8453 for Base)",
    )

    # Top voters endpoint settings
    DEFAULT_TOP_VOTERS_LIMIT: ClassVar[int] = 10
    MAX_TOP_VOTERS_LIMIT: ClassVar[int] = 50
    MIN_TOP_VOTERS_LIMIT: ClassVar[int] = 1
    default_top_voters_limit: int = DEFAULT_TOP_VOTERS_LIMIT
    max_top_voters_limit: int = MAX_TOP_VOTERS_LIMIT
    min_top_voters_limit: int = MIN_TOP_VOTERS_LIMIT

    # Safe wallet configuration
    # the safe_addresses come from the pearl runtime env
    # the agent_address comes from The private key is stored in a file called ethereum_private_key.txt in the agent's working directory
    safe_addresses: Dict[str, str] = Field(
        default_factory=dict, description="Parsed from SAFE_CONTRACT_ADDRESSES"
    )
    agent_address: Optional[str] = Field(
        default=None, description="The agent's EOA address"
    )

    # DAO monitoring - removed from Pydantic fields to avoid JSON parsing issues
    # Use the monitored_daos_list property instead
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
    max_proposals_per_run: int = Field(
        default=3,
        ge=1,
        le=10,
        description="Maximum proposals to process per agent run",
    )
    agent_confidence_threshold: float = Field(
        default=0.7,
        ge=0.0,
        le=1.0,
        description="Default confidence threshold for agent voting decisions",
    )
    proposal_fetch_timeout: int = Field(
        default=30,
        gt=0,
        description="Timeout for proposal fetching in seconds",
    )
    vote_execution_timeout: int = Field(
        default=60,
        gt=0,
        description="Timeout for vote execution in seconds",
    )
    max_retry_attempts: int = Field(
        default=3,
        ge=0,
        le=10,
        description="Maximum retry attempts for failed operations",
    )
    retry_delay_seconds: int = Field(
        default=5,
        gt=0,
        description="Delay between retry attempts in seconds",
    )

    # File output configuration
    decision_output_dir: str = Field(
        default="decisions",
        alias="DECISION_OUTPUT_DIR",
        description="Directory for voting decision files",
    )
    decision_file_format: str = Field(
        default="json",
        alias="DECISION_FILE_FORMAT",
        description="Format for decision files (json)",
    )
    max_decision_files: int = Field(
        default=100,
        ge=1,
        le=1000,
        alias="MAX_DECISION_FILES",
        description="Maximum number of decision files to retain",
    )

    # Health check configuration
    HEALTH_CHECK_PORT: int = Field(
        default=8716,
        ge=1,
        le=65535,
        alias="HEALTH_CHECK_PORT",
        description="Port for Pearl-compliant health check endpoint",
    )
    HEALTH_CHECK_PATH: str = Field(
        default="/healthcheck",
        alias="HEALTH_CHECK_PATH",
        description="Path for Pearl-compliant health check endpoint",
    )
    FAST_TRANSITION_THRESHOLD: int = Field(
        default=5,
        gt=0,
        alias="FAST_TRANSITION_THRESHOLD",
        description="Threshold in seconds for detecting fast state transitions",
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
    celo_ledger_rpc: Optional[str] = Field(
        default=None,
        alias="CELO_LEDGER_RPC",
        description="Celo chain RPC endpoint",
    )

    # Legacy compatibility fields for existing tests
    chain_name: str = Field(
        default="celo",
        description="Default blockchain name for backwards compatibility",
    )

    @property
    def celo_rpc(self) -> str:
        """Legacy property for celo_rpc compatibility.

        Returns celo_ledger_rpc value or empty string for backwards compatibility.
        """
        return self.celo_ledger_rpc or ""

    # EAS (Ethereum Attestation Service) configuration
    eas_contract_address: Optional[str] = Field(
        default=None,
        alias="EAS_CONTRACT_ADDRESS",
        description="EAS contract address on Base network",
    )
    eas_schema_uid: Optional[str] = Field(
        default=None,
        alias="EAS_SCHEMA_UID",
        description="EAS schema UID for vote attestations",
    )
    base_safe_address: Optional[str] = Field(
        default=None,
        alias="BASE_SAFE_ADDRESS",
        description="Agent's Gnosis Safe address on Base network",
    )
    base_rpc_url: Optional[str] = Field(
        default=None,
        alias="BASE_RPC_URL",
        description="Base network RPC endpoint (alternative to BASE_LEDGER_RPC)",
    )

    # AttestationTracker Configuration
    attestation_tracker_address: Optional[str] = Field(
        default=None,
        alias="ATTESTATION_TRACKER_ADDRESS",
        description="AttestationTracker wrapper contract address on Base network. If set, attestations will be routed through this contract.",
    )
    attestation_chain: str = Field(
        default="base",
        alias="ATTESTATION_CHAIN",
        description="Chain to use for attestation transactions (e.g., 'base', 'ethereum')",
    )

    @field_validator("log_level", mode="before")
    @classmethod
    def validate_log_level(cls, v):
        """Validate log level is one of the Pearl-compliant levels."""
        if v is None or (isinstance(v, str) and not v.strip()):
            return cls.DEFAULT_LOG_LEVEL
        if isinstance(v, str):
            v = v.upper().strip()
            if v not in cls.VALID_LOG_LEVELS:
                raise ValueError(
                    f"Invalid log level: {v}. Must be one of {cls.VALID_LOG_LEVELS}"
                )
            return v
        return cls.DEFAULT_LOG_LEVEL

    @field_validator("log_file_path", mode="before")
    @classmethod
    def validate_log_file_path(cls, v):
        """Validate log file path is not empty."""
        if v is None or (isinstance(v, str) and not v.strip()):
            return cls.DEFAULT_LOG_FILE_PATH
        if isinstance(v, str):
            if v.strip().lower() == "none":
                raise ValueError("Log file path cannot be empty")
            return v.strip()
        return cls.DEFAULT_LOG_FILE_PATH

    @field_validator("HEALTH_CHECK_TIMEOUT", mode="before")
    @classmethod
    def validate_health_check_timeout(cls, v):
        """Validate health check timeout is a positive integer."""
        if v is None:
            return 50  # Default value
        try:
            timeout = int(v)
            if timeout <= 0:
                raise ValueError(
                    f"Health check timeout must be positive, got {timeout}"
                )
            return timeout
        except (ValueError, TypeError):
            if isinstance(v, str) and not v.isdigit():
                raise ValueError(f"Invalid timeout value: {v}")
            raise

    @field_validator("HEALTH_CHECK_ENABLED", mode="before")
    @classmethod
    def validate_health_check_enabled(cls, v):
        """Validate health check enabled is boolean type."""
        if v is None:
            return True  # Default value
        if isinstance(v, bool):
            return v
        if isinstance(v, str):
            if v.lower() in ["true", "1", "yes"]:
                return True
            elif v.lower() in ["false", "0", "no"]:
                return False
        if isinstance(v, (int, float)):
            return bool(v)
        raise ValueError(f"Health check enabled must be boolean, got {type(v)}: {v}")

    @field_validator("PEARL_LOG_FORMAT", mode="before")
    @classmethod
    def validate_pearl_log_format(cls, v):
        """Validate Pearl log format is non-empty string."""
        if v is None or (isinstance(v, str) and not v.strip()):
            return (
                "[%Y-%m-%d %H:%M:%S,%f] [%levelname] [agent] %message"  # Default value
            )
        if isinstance(v, str):
            return v.strip()
        raise ValueError(f"Pearl log format must be string, got {type(v)}: {v}")

    @field_validator("HEALTH_CHECK_PORT", mode="before")
    @classmethod
    def validate_health_check_port(cls, v):
        """Validate health check port is a valid integer."""
        if v is None:
            return 8716  # Default value
        try:
            port = int(v)
            if not (1 <= port <= 65535):
                raise ValueError(f"Port must be between 1 and 65535, got {port}")
            return port
        except (ValueError, TypeError):
            if isinstance(v, str) and not v.isdigit():
                raise ValueError(f"Invalid port value: {v}")
            raise

    @field_validator("FAST_TRANSITION_THRESHOLD", mode="before")
    @classmethod
    def validate_fast_transition_threshold(cls, v):
        """Validate fast transition threshold is a valid positive integer."""
        if v is None:
            return 5  # Default value
        try:
            threshold = int(v)
            if threshold <= 0:
                raise ValueError(
                    f"Fast transition threshold must be positive, got {threshold}"
                )
            return threshold
        except (ValueError, TypeError):
            if isinstance(v, str) and not v.isdigit():
                raise ValueError(f"Invalid threshold value: {v}")
            raise

    @field_validator("voting_strategy")
    @classmethod
    def validate_voting_strategy(cls, v):
        """Validate voting strategy is one of the allowed values."""
        valid_strategies = ["balanced", "conservative", "aggressive"]
        if v not in valid_strategies:
            raise ValueError(
                f"Invalid voting strategy: {v}. Must be one of {valid_strategies}"
            )
        return v

    @model_validator(mode="after")
    def parse_env_settings(self):
        """Parse environment-specific settings after model initialization."""
        self._parse_safe_addresses()
        self._parse_agent_address()
        self._parse_vote_threshold()
        self._parse_intervals()
        self._parse_agent_run_config()
        self._parse_pearl_logging_config()
        self._parse_olas_config()
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
        self._parse_agent_confidence_threshold()
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

    def _parse_agent_confidence_threshold(self):
        """Parse agent confidence threshold from AGENT_CONFIDENCE_THRESHOLD environment variable."""
        confidence_threshold_env = os.getenv("AGENT_CONFIDENCE_THRESHOLD")
        if confidence_threshold_env:
            threshold = float(confidence_threshold_env)
            if not (0.0 <= threshold <= 1.0):
                raise ValueError(
                    f"agent_confidence_threshold must be between 0.0 and 1.0, got {threshold}"
                )
            self.agent_confidence_threshold = threshold

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
            "agent_confidence_threshold": self.agent_confidence_threshold,
            "proposal_fetch_timeout": self.proposal_fetch_timeout,
            "vote_execution_timeout": self.vote_execution_timeout,
            "max_retry_attempts": self.max_retry_attempts,
            "retry_delay_seconds": self.retry_delay_seconds,
        }

    def _parse_pearl_logging_config(self):
        """Parse Pearl logging configuration from environment variables."""
        log_level_env = os.getenv("LOG_LEVEL")
        if log_level_env:
            level = log_level_env.upper()
            if level not in self.VALID_LOG_LEVELS:
                raise ValueError(
                    f"Invalid log level: {level}. Must be one of {self.VALID_LOG_LEVELS}"
                )
            self.log_level = level

        log_file_path_env = os.getenv("LOG_FILE_PATH")
        if log_file_path_env:
            if (
                not log_file_path_env.strip()
                or log_file_path_env.strip().lower() == "none"
            ):
                raise ValueError("Log file path cannot be empty")
            self.log_file_path = log_file_path_env.strip()

    def get_pearl_logging_config(self) -> Dict[str, str]:
        """Get Pearl logging configuration as a dictionary.

        Returns:
            Dict containing Pearl logging configuration values.
        """
        return {
            "log_level": self.log_level,
            "log_file_path": self.log_file_path,
        }

    def get_base_rpc_endpoint(self) -> Optional[str]:
        """Get Base network RPC endpoint.

        Returns:
            Base RPC endpoint from either base_rpc_url or base_ledger_rpc.
        """
        return self.base_rpc_url or self.base_ledger_rpc

    def validate_attestation_environment(self) -> bool:
        """Validate that all required environment variables for vote attestation are present.

        This method checks for critical environment variables needed for the vote
        attestation system to function properly in production.

        Returns:
            True if all required variables are present and valid.

        Raises:
            ValueError: If any required environment variable is missing or invalid.
        """
        missing_vars = []

        # Check required OpenRouter API key for AI voting decisions
        if not self.openrouter_api_key:
            missing_vars.append("OPENROUTER_API_KEY")

        # Check required EAS configuration for on-chain attestations
        if not self.eas_contract_address:
            missing_vars.append("EAS_CONTRACT_ADDRESS")

        if not self.eas_schema_uid:
            missing_vars.append("EAS_SCHEMA_UID")

        # Check required Base network configuration for attestation transactions
        if not self.base_safe_address:
            missing_vars.append("BASE_SAFE_ADDRESS")

        # Check that at least one Base RPC endpoint is configured
        if not self.get_base_rpc_endpoint():
            missing_vars.append("BASE_RPC_URL or BASE_LEDGER_RPC")

        if missing_vars:
            missing_vars_str = ", ".join(missing_vars)
            raise ValueError(
                f"Missing required environment variables for vote attestation system: {missing_vars_str}. "
                f"Please configure these variables in your .env file. See .env.example for reference."
            )

        # Validate EAS contract address format (should be a valid Ethereum address)
        if self.eas_contract_address and not self.eas_contract_address.startswith("0x"):
            raise ValueError(
                f"Invalid EAS_CONTRACT_ADDRESS format: {self.eas_contract_address}. "
                f"Must be a valid Ethereum address starting with '0x'."
            )

        # Validate EAS schema UID format (should be a 32-byte hex string with 0x prefix)
        if self.eas_schema_uid and not (
            self.eas_schema_uid.startswith("0x") and len(self.eas_schema_uid) == 66
        ):
            raise ValueError(
                f"Invalid EAS_SCHEMA_UID format: {self.eas_schema_uid}. "
                f"Must be a 32-byte hex string with '0x' prefix (66 characters total)."
            )

        # Validate Base Safe address format
        if self.base_safe_address and not self.base_safe_address.startswith("0x"):
            raise ValueError(
                f"Invalid BASE_SAFE_ADDRESS format: {self.base_safe_address}. "
                f"Must be a valid Ethereum address starting with '0x'."
            )

        return True

    @model_validator(mode="after")
    def validate_attestation_tracker_config(self):
        """Validate AttestationTracker configuration."""
        if self.attestation_tracker_address:
            # Validate address format - must be a valid Web3 address
            if not Web3.is_address(self.attestation_tracker_address):
                raise ValueError(
                    f"Invalid ATTESTATION_TRACKER_ADDRESS: {self.attestation_tracker_address}"
                )
            # Convert to checksum address for consistency
            self.attestation_tracker_address = Web3.to_checksum_address(
                self.attestation_tracker_address
            )
        return self

    def _parse_olas_config(self):
        """Parse Olas-specific configuration from environment variables with prefix support."""
        # Parse snapshot_api_key with prefix support
        snapshot_api_key_env = get_env_with_prefix("SNAPSHOT_API_KEY")
        if snapshot_api_key_env:
            self.snapshot_api_key = snapshot_api_key_env

        # Parse voting_strategy with prefix support
        voting_strategy_env = get_env_with_prefix("VOTING_STRATEGY")
        if voting_strategy_env:
            self.voting_strategy = voting_strategy_env

        # Parse dao_addresses with prefix support
        dao_addresses_env = get_env_with_prefix("DAO_ADDRESSES")
        if dao_addresses_env:
            # Split comma-separated addresses and clean them
            addresses = [
                addr.strip() for addr in dao_addresses_env.split(",") if addr.strip()
            ]
            self.dao_addresses = addresses

    @property
    def effective_openrouter_api_key(self) -> Optional[str]:
        """Get API key with user preference priority.

        Returns:
            User-provided API key if available, otherwise environment key
        """
        # Try user key first (would be loaded from StateManager)
        if hasattr(self, "_user_api_key") and self._user_api_key:
            return self._user_api_key
        # Fall back to environment
        return self.openrouter_api_key

    def reload_with_user_key(self, user_key: Optional[str]) -> None:
        """Update user API key and trigger reload.

        Args:
            user_key: User-provided API key or None to clear
        """
        self._user_api_key = user_key
        # Use existing reload mechanism
        self.reload_config()


# Global settings instance
settings = Settings()
