// SPDX-License-Identifier: MIT
pragma solidity 0.8.24;

interface IERC20 {
    function transfer(address to, uint256 amount) external returns (bool);
    function transferFrom(address from, address to, uint256 amount) external returns (bool);
    function balanceOf(address account) external view returns (uint256);
    function approve(address spender, uint256 amount) external returns (bool);
}

interface IServiceRegistry {
    struct Service {
        address serviceOwner;
        bytes32 configHash;
        uint32 threshold;
        uint32 maxNumServices;
        uint32 numActiveInstances;
        uint8 serviceState;
        address[] agentIds;
    }
    
    function getService(uint256 serviceId) external view returns (Service memory);
    function exists(uint256 serviceId) external view returns (bool);
}

interface IActivityChecker {
    function getMultisigNonces(address multisig) external view returns (uint256[] memory nonces);
    function isServiceStakingReady(uint256 serviceId) external view returns (bool);
}

/**
 * @title StakingParams
 * @dev Struct to hold staking initialization parameters
 */
struct StakingParams {
    bytes32 metadataHash;           // Metadata hash for this staking instance
    uint256 maxNumServices;         // Maximum number of services that can stake
    uint256 rewardsPerSecond;       // Rewards per second in wei
    uint256 minStakingDeposit;      // Minimum staking deposit required
    uint256 minNumStakingPeriods;   // Minimum number of staking periods
    uint256 maxNumInactivityPeriods; // Max periods of inactivity before eviction
    uint256 livenessPeriod;         // Period length in seconds
    uint256 timeForEmissions;       // Total time for emissions
    uint256 numAgentInstances;      // Number of agent instances per service
    uint32[] agentIds;              // Required agent IDs (empty for no requirement)
    uint256 threshold;              // Service threshold requirement
    bytes32 configHash;             // Required config hash
    bytes32 proxyHash;              // Required proxy hash
    address serviceRegistry;        // ServiceRegistry contract address
    address activityChecker;        // ActivityChecker contract address
}

/**
 * @title ServiceInfo
 * @dev Struct to track staked service information
 */
struct ServiceInfo {
    address multisig;              // Service multisig address
    address owner;                 // Service owner
    uint32[] nonces;              // Service nonces snapshot at staking
    uint256 tsStart;              // Timestamp when staking started
    uint256 reward;               // Accumulated reward
    uint256 inactivity;           // Number of inactive periods
}

/**
 * @title StakingBase
 * @dev Base contract for token staking functionality with reward distribution
 * 
 * Core Features:
 * - Service staking with configurable parameters
 * - Activity-based reward calculation
 * - Checkpoint system for reward distribution
 * - Inactivity tracking and eviction
 * - Minimum staking periods enforcement
 */
abstract contract StakingBase {
    // Service states
    enum ServiceStakingState {
        Unstaked,
        Staked, 
        Evicted
    }

    // Events
    event ServiceStaked(uint256 indexed serviceId, address indexed owner, address indexed multisig, uint256 nonces);
    event ServiceUnstaked(uint256 indexed serviceId, address indexed owner, address indexed multisig, uint256 reward);
    event Checkpoint(uint256[] serviceIds, uint256[][] multisigNonces, uint256[] rewards, uint256 epochCounter);
    event ServiceEvicted(uint256 indexed serviceId, address indexed owner, address indexed multisig, uint256 inactivity);

    // Core staking parameters
    bytes32 public metadataHash;
    uint256 public maxNumServices;
    uint256 public rewardsPerSecond;
    uint256 public minStakingDeposit;
    uint256 public minNumStakingPeriods;
    uint256 public maxNumInactivityPeriods;
    uint256 public livenessPeriod;
    uint256 public timeForEmissions;
    uint256 public numAgentInstances;
    uint32[] public agentIds;
    uint256 public threshold;
    bytes32 public configHash;
    bytes32 public proxyHash;
    
    // Contract references
    address public immutable serviceRegistry;
    address public immutable activityChecker;
    
    // State tracking
    mapping(uint256 => ServiceInfo) public mapServiceInfo;
    mapping(uint256 => ServiceStakingState) public mapServiceStakingState;
    
    uint256[] public setServiceIds;
    uint256 public tsCheckpoint;
    uint256 public epochCounter;
    uint256 public balance;
    uint256 public availableRewards;
    bool public stakingStarted;

    // Errors
    error ZeroAddress();
    error ZeroValue();
    error ServiceNotExists(uint256 serviceId);
    error ServiceAlreadyStaked(uint256 serviceId);
    error ServiceNotStaked(uint256 serviceId);
    error InsufficientStakingDeposit(uint256 provided, uint256 required);
    error WrongServiceConfiguration(uint256 serviceId);
    error UnstakingNotAllowed(uint256 serviceId);
    error RewardsFundingFailed(uint256 amount);
    error MaxNumServicesReached(uint256 max);
    error ServiceEvictionError(uint256 serviceId);
    error StakingNotStarted();

    /**
     * @dev Constructor for StakingBase
     * @param _stakingParams Struct containing all staking parameters
     */
    constructor(StakingParams memory _stakingParams) {
        // Validate parameters
        if (_stakingParams.maxNumServices == 0) revert ZeroValue();
        if (_stakingParams.rewardsPerSecond == 0) revert ZeroValue();
        if (_stakingParams.minStakingDeposit == 0) revert ZeroValue();
        if (_stakingParams.livenessPeriod == 0) revert ZeroValue();
        if (_stakingParams.timeForEmissions == 0) revert ZeroValue();
        if (_stakingParams.serviceRegistry == address(0)) revert ZeroAddress();

        // Set immutable values
        serviceRegistry = _stakingParams.serviceRegistry;
        activityChecker = _stakingParams.activityChecker;

        // Set staking parameters
        metadataHash = _stakingParams.metadataHash;
        maxNumServices = _stakingParams.maxNumServices;
        rewardsPerSecond = _stakingParams.rewardsPerSecond;
        minStakingDeposit = _stakingParams.minStakingDeposit;
        minNumStakingPeriods = _stakingParams.minNumStakingPeriods;
        maxNumInactivityPeriods = _stakingParams.maxNumInactivityPeriods;
        livenessPeriod = _stakingParams.livenessPeriod;
        timeForEmissions = _stakingParams.timeForEmissions;
        numAgentInstances = _stakingParams.numAgentInstances;
        threshold = _stakingParams.threshold;
        configHash = _stakingParams.configHash;
        proxyHash = _stakingParams.proxyHash;

        // Store agent IDs if provided
        for (uint256 i = 0; i < _stakingParams.agentIds.length; i++) {
            agentIds.push(_stakingParams.agentIds[i]);
        }

        // Initialize checkpoint timestamp
        tsCheckpoint = block.timestamp;
    }

    /**
     * @dev Abstract function to handle token deposits during staking
     * Must be implemented by concrete contracts (StakingToken, StakingNativeToken)
     */
    function _withdraw(address to, uint256 amount) internal virtual;

    /**
     * @dev Abstract function to handle token withdrawals during unstaking
     * Must be implemented by concrete contracts (StakingToken, StakingNativeToken)
     */
    function _deposit(address from, uint256 amount) internal virtual;

    /**
     * @dev Start staking by funding the contract with rewards
     * @param amount Amount of reward tokens to fund
     */
    function fundRewards(uint256 amount) external {
        if (amount == 0) revert ZeroValue();
        
        _deposit(msg.sender, amount);
        availableRewards += amount;
        stakingStarted = true;
    }

    /**
     * @dev Stake a service with required deposit
     * @param serviceId Service ID to stake
     */
    function stake(uint256 serviceId) external {
        if (!stakingStarted) revert StakingNotStarted();
        
        // Validate service exists
        if (!IServiceRegistry(serviceRegistry).exists(serviceId)) {
            revert ServiceNotExists(serviceId);
        }

        // Get service details
        IServiceRegistry.Service memory service = IServiceRegistry(serviceRegistry).getService(serviceId);
        
        // Validate service owner
        if (service.serviceOwner != msg.sender) {
            revert WrongServiceConfiguration(serviceId);
        }

        // Validate service is not already staked
        if (mapServiceStakingState[serviceId] != ServiceStakingState.Unstaked) {
            revert ServiceAlreadyStaked(serviceId);
        }

        // Check max services limit
        if (setServiceIds.length >= maxNumServices) {
            revert MaxNumServicesReached(maxNumServices);
        }

        // Validate service configuration if requirements are set
        if (agentIds.length > 0) {
            // Check agent IDs match requirements (simplified validation)
            if (service.agentIds.length != agentIds.length) {
                revert WrongServiceConfiguration(serviceId);
            }
        }

        if (threshold > 0 && service.threshold != threshold) {
            revert WrongServiceConfiguration(serviceId);
        }

        if (configHash != bytes32(0) && service.configHash != configHash) {
            revert WrongServiceConfiguration(serviceId);
        }

        // Get multisig address from first agent instance (simplified)
        address multisig = service.agentIds.length > 0 ? service.agentIds[0] : msg.sender;

        // Validate proxy hash if set
        if (proxyHash != bytes32(0)) {
            bytes32 currentProxyHash = keccak256(abi.encode(multisig));
            if (currentProxyHash != proxyHash) {
                revert WrongServiceConfiguration(serviceId);
            }
        }

        // Handle deposit
        _deposit(msg.sender, minStakingDeposit);
        balance += minStakingDeposit;

        // Get activity checker nonces if available
        uint32[] memory nonces;
        if (activityChecker != address(0)) {
            try IActivityChecker(activityChecker).getMultisigNonces(multisig) returns (uint256[] memory _nonces) {
                nonces = new uint32[](_nonces.length);
                for (uint i = 0; i < _nonces.length; i++) {
                    nonces[i] = uint32(_nonces[i]);
                }
            } catch {
                // If getting nonces fails, use empty array
                nonces = new uint32[](0);
            }
        } else {
            nonces = new uint32[](0);
        }

        // Store service info
        mapServiceInfo[serviceId] = ServiceInfo({
            multisig: multisig,
            owner: msg.sender,
            nonces: nonces,
            tsStart: block.timestamp,
            reward: 0,
            inactivity: 0
        });

        mapServiceStakingState[serviceId] = ServiceStakingState.Staked;
        setServiceIds.push(serviceId);

        emit ServiceStaked(serviceId, msg.sender, multisig, nonces.length);
    }

    /**
     * @dev Unstake a service and claim rewards
     * @param serviceId Service ID to unstake
     * @return reward Amount of reward received
     */
    function unstake(uint256 serviceId) external returns (uint256 reward) {
        ServiceInfo storage serviceInfo = mapServiceInfo[serviceId];
        
        // Validate service is staked and owned by caller
        if (mapServiceStakingState[serviceId] != ServiceStakingState.Staked) {
            revert ServiceNotStaked(serviceId);
        }
        
        if (serviceInfo.owner != msg.sender) {
            revert WrongServiceConfiguration(serviceId);
        }

        // Check minimum staking period
        if (minNumStakingPeriods > 0) {
            uint256 numStakingPeriods = (block.timestamp - serviceInfo.tsStart) / livenessPeriod;
            if (numStakingPeriods < minNumStakingPeriods) {
                revert UnstakingNotAllowed(serviceId);
            }
        }

        // Calculate final reward
        reward = calculateServiceStakingReward(serviceId);
        
        // Update balances
        if (reward > 0) {
            if (reward > availableRewards) {
                reward = availableRewards;
            }
            availableRewards -= reward;
        }
        
        // Return staking deposit plus rewards
        uint256 totalWithdrawal = minStakingDeposit + reward;
        if (totalWithdrawal > balance) {
            totalWithdrawal = balance;
        }
        balance -= totalWithdrawal;
        
        _withdraw(msg.sender, totalWithdrawal);

        // Clean up service state
        _removeServiceFromSet(serviceId);
        delete mapServiceInfo[serviceId];
        mapServiceStakingState[serviceId] = ServiceStakingState.Unstaked;

        emit ServiceUnstaked(serviceId, msg.sender, serviceInfo.multisig, reward);
    }

    /**
     * @dev Execute checkpoint to calculate and distribute rewards
     * @return serviceIds Array of processed service IDs
     * @return multisigNonces Array of multisig nonces for each service
     * @return rewards Array of rewards calculated for each service
     * @return epochLength Current epoch counter
     */
    function checkpoint() external returns (
        uint256[] memory serviceIds,
        uint256[][] memory multisigNonces,
        uint256[] memory rewards,
        uint256 epochLength
    ) {
        // Calculate time since last checkpoint
        uint256 ts = block.timestamp;
        if (ts <= tsCheckpoint) {
            // Return empty arrays if no time has passed
            return (new uint256[](0), new uint256[][](0), new uint256[](0), epochCounter);
        }

        epochCounter++;
        uint256 numServices = setServiceIds.length;
        
        serviceIds = new uint256[](numServices);
        multisigNonces = new uint256[][](numServices);
        rewards = new uint256[](numServices);

        for (uint256 i = 0; i < numServices; i++) {
            uint256 serviceId = setServiceIds[i];
            ServiceInfo storage serviceInfo = mapServiceInfo[serviceId];
            
            serviceIds[i] = serviceId;
            
            // Get current nonces
            if (activityChecker != address(0)) {
                try IActivityChecker(activityChecker).getMultisigNonces(serviceInfo.multisig) returns (uint256[] memory currentNonces) {
                    multisigNonces[i] = currentNonces;
                    
                    // Simple activity check: has nonces changed?
                    bool hasActivity = false;
                    if (currentNonces.length > 0 && serviceInfo.nonces.length > 0) {
                        for (uint j = 0; j < currentNonces.length && j < serviceInfo.nonces.length; j++) {
                            if (currentNonces[j] > serviceInfo.nonces[j]) {
                                hasActivity = true;
                                break;
                            }
                        }
                    } else if (currentNonces.length > serviceInfo.nonces.length) {
                        hasActivity = true;
                    }
                    
                    if (hasActivity) {
                        // Calculate reward for active period
                        uint256 periodReward = rewardsPerSecond * livenessPeriod;
                        if (periodReward > availableRewards) {
                            periodReward = availableRewards;
                        }
                        
                        serviceInfo.reward += periodReward;
                        availableRewards -= periodReward;
                        serviceInfo.inactivity = 0;
                        
                        // Update nonces snapshot
                        delete serviceInfo.nonces;
                        for (uint k = 0; k < currentNonces.length; k++) {
                            serviceInfo.nonces.push(uint32(currentNonces[k]));
                        }
                    } else {
                        // No activity detected
                        serviceInfo.inactivity++;
                        
                        // Check for eviction due to inactivity
                        if (maxNumInactivityPeriods > 0 && serviceInfo.inactivity >= maxNumInactivityPeriods) {
                            mapServiceStakingState[serviceId] = ServiceStakingState.Evicted;
                            emit ServiceEvicted(serviceId, serviceInfo.owner, serviceInfo.multisig, serviceInfo.inactivity);
                        }
                    }
                } catch {
                    // If activity check fails, treat as no activity
                    multisigNonces[i] = new uint256[](0);
                    serviceInfo.inactivity++;
                }
            } else {
                // No activity checker, always give rewards
                multisigNonces[i] = new uint256[](0);
                uint256 periodReward = rewardsPerSecond * livenessPeriod;
                if (periodReward > availableRewards) {
                    periodReward = availableRewards;
                }
                serviceInfo.reward += periodReward;
                availableRewards -= periodReward;
            }
            
            rewards[i] = serviceInfo.reward;
        }

        tsCheckpoint = ts;
        
        emit Checkpoint(serviceIds, multisigNonces, rewards, epochCounter);
        return (serviceIds, multisigNonces, rewards, epochCounter);
    }

    /**
     * @dev Calculate current staking reward for a service
     * @param serviceId Service ID to calculate reward for
     * @return reward Current accumulated reward
     */
    function calculateServiceStakingReward(uint256 serviceId) public view returns (uint256 reward) {
        ServiceInfo storage serviceInfo = mapServiceInfo[serviceId];
        
        if (mapServiceStakingState[serviceId] != ServiceStakingState.Staked) {
            return 0;
        }

        reward = serviceInfo.reward;
        
        // Add pending reward for current period
        if (rewardsPerSecond > 0 && block.timestamp > tsCheckpoint) {
            uint256 timeSinceCheckpoint = block.timestamp - tsCheckpoint;
            uint256 periodsElapsed = timeSinceCheckpoint / livenessPeriod;
            
            if (periodsElapsed > 0) {
                uint256 pendingReward = rewardsPerSecond * livenessPeriod * periodsElapsed;
                if (pendingReward <= availableRewards) {
                    reward += pendingReward;
                }
            }
        }
    }

    /**
     * @dev Get detailed service information
     * @param serviceId Service ID to get info for
     * @return multisig Service multisig address
     * @return owner Service owner address
     * @return nonces Current nonces count
     * @return tsStart Staking start timestamp
     * @return reward Accumulated reward
     * @return inactivity Number of inactive periods
     */
    function getServiceInfo(uint256 serviceId) external view returns (
        address multisig,
        address owner,
        uint32 nonces,
        uint256 tsStart,
        uint256 reward,
        uint256 inactivity
    ) {
        ServiceInfo storage info = mapServiceInfo[serviceId];
        return (
            info.multisig,
            info.owner,
            uint32(info.nonces.length),
            info.tsStart,
            info.reward,
            info.inactivity
        );
    }

    /**
     * @dev Get array of currently staked service IDs
     * @return Array of service IDs
     */
    function getServiceIds() external view returns (uint256[] memory) {
        return setServiceIds;
    }

    /**
     * @dev Remove a service from the active services set
     * @param serviceId Service ID to remove
     */
    function _removeServiceFromSet(uint256 serviceId) internal {
        uint256 length = setServiceIds.length;
        for (uint256 i = 0; i < length; i++) {
            if (setServiceIds[i] == serviceId) {
                setServiceIds[i] = setServiceIds[length - 1];
                setServiceIds.pop();
                break;
            }
        }
    }
}
