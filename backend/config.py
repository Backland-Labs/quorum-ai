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

    # Governor configuration
    governor_voting_enabled: bool = True
    batch_encoding_enabled: bool = True
    max_batch_size: int = 50
    governor_cache_ttl: int = 7200  # 2 hours
    vote_encoding_cache_ttl: int = 300  # 5 minutes
    
    # RPC endpoints
    ethereum_rpc_url: Optional[str] = None
    
    # Governor registry (predefined governor contracts)
    governor_registry: Dict[str, str] = Field(
        default_factory=lambda: {
            "compound-governor-bravo": "0xc0Da02939E1441F497fd74F78cE7Decb17B66529",
            "compound-governor": "0x315d9C2E24C47fC8F2bc21C18D26B4e4A37be5c5",
            "aave-governance": "0xEC568fffba86c094cf06b22134B23074DFE2252c",
            "uniswap-governance": "0x408ED6354d4973f66138C91495F2f2FCbd8724C3",
        }
    )

    # Top organizations configuration
    DEFAULT_TOP_ORGANIZATIONS: ClassVar[str] = "compound,nounsdao,arbitrum"
    top_organizations_env: str = DEFAULT_TOP_ORGANIZATIONS

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
        # Runtime assertions for configuration parsing
        assert hasattr(self, 'safe_addresses'), "Safe addresses attribute must exist"
        assert hasattr(self, 'monitored_daos'), "Monitored DAOs attribute must exist"
        
        self._parse_safe_addresses()
        self._parse_agent_address()
        self._parse_vote_threshold()
        self._parse_intervals()
        self._parse_governor_settings()
        
        # Runtime assertion: validate successful parsing
        assert isinstance(self.governor_registry, dict), "Governor registry must be dict"
        
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

    def _parse_governor_settings(self):
        """Parse governor-related settings from environment variables."""
        self._parse_governor_feature_flags()
        self._parse_governor_batch_settings()
        self._parse_governor_rpc_endpoints()
        self._parse_governor_registry()
    
    def _parse_governor_feature_flags(self):
        """Parse governor feature flags from environment."""
        # Governor voting enabled
        governor_voting_env = os.getenv("GOVERNOR_VOTING_ENABLED")
        if governor_voting_env is not None:
            self.governor_voting_enabled = governor_voting_env.lower() in ("true", "1", "yes")

        # Batch encoding enabled
        batch_encoding_env = os.getenv("BATCH_ENCODING_ENABLED")
        if batch_encoding_env is not None:
            self.batch_encoding_enabled = batch_encoding_env.lower() in ("true", "1", "yes")
    
    def _parse_governor_batch_settings(self):
        """Parse governor batch processing settings."""
        # Max batch size
        max_batch_env = os.getenv("MAX_BATCH_SIZE")
        if max_batch_env:
            batch_size = int(max_batch_env)
            if batch_size <= 0:
                raise ValueError(f"max_batch_size must be positive, got {batch_size}")
            self.max_batch_size = batch_size
    
    def _parse_governor_rpc_endpoints(self):
        """Parse RPC endpoints for governor operations."""
        # RPC endpoints
        ethereum_rpc_env = os.getenv("ETHEREUM_RPC_URL")
        if ethereum_rpc_env:
            self.ethereum_rpc_url = ethereum_rpc_env
    
    def _parse_governor_registry(self):
        """Parse governor registry from environment variables."""
        # Governor registry from environment
        governor_registry_env = os.getenv("GOVERNOR_REGISTRY")
        if governor_registry_env:
            try:
                # Expected format: "dao1:address1,dao2:address2"
                registry = self._parse_registry_string(governor_registry_env)
                if registry:
                    self.governor_registry.update(registry)
            except Exception as e:
                raise ValueError(f"Invalid GOVERNOR_REGISTRY format: {e}")
    
    def _parse_registry_string(self, registry_string: str) -> Dict[str, str]:
        """Parse registry string into DAO->address mapping."""
        registry = {}
        for pair in registry_string.split(","):
            if ":" in pair:
                dao, address = pair.split(":", 1)
                dao = dao.strip()
                address = address.strip()
                if dao and address:
                    registry[dao] = address
        return registry

    @property
    def top_organizations(self) -> List[str]:
        """Parse comma-separated string to list."""
        return [
            org.strip() for org in self.top_organizations_env.split(",") if org.strip()
        ]

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

    def validate_governor_addresses(self) -> Dict[str, bool]:
        """Validate governor contract addresses in registry."""
        validation_results = {}
        
        for dao_id, address in self.governor_registry.items():
            validation_results[dao_id] = self._is_valid_ethereum_address(address)
        
        return validation_results
    
    def _is_valid_ethereum_address(self, address: str) -> bool:
        """Validate a single Ethereum address format."""
        try:
            # Basic Ethereum address validation
            if not address.startswith("0x"):
                return False
            
            # Check length (42 characters for 0x + 40 hex chars)
            if len(address) != 42:
                return False
            
            # Check if it's valid hex
            int(address[2:], 16)
            return True
            
        except (ValueError, TypeError):
            return False

    @property
    def rpc_endpoints(self) -> Dict[str, Optional[str]]:
        """Get RPC endpoints for different networks."""
        return self._build_rpc_endpoints_mapping()
    
    def _build_rpc_endpoints_mapping(self) -> Dict[str, Optional[str]]:
        """Build mapping of network names to RPC endpoints."""
        return {
            "ethereum": self.ethereum_rpc_url,
            # Add more networks as needed
        }
    
    def get_governor_by_dao_id(self, dao_id: str) -> Optional[str]:
        """Get governor contract address for a specific DAO ID."""
        # Runtime assertions for governor registry access
        assert dao_id, "DAO ID cannot be empty"
        assert isinstance(dao_id, str), "DAO ID must be string"
        
        return self.governor_registry.get(dao_id)
    
    def is_governor_voting_enabled_for_dao(self, dao_id: str) -> bool:
        """Check if governor voting is enabled for a specific DAO."""
        # Runtime assertions for feature flag check
        assert dao_id, "DAO ID cannot be empty"
        assert isinstance(dao_id, str), "DAO ID must be string"
        
        # Check global flag and DAO-specific configuration
        return self.governor_voting_enabled and dao_id in self.governor_registry


# Global settings instance
settings = Settings()
