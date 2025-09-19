// SPDX-License-Identifier: MIT
pragma solidity 0.8.24;

import {Test, console} from "forge-std/Test.sol";
import "../src/StakingToken.sol";

/**
 * @title StakingForkComprehensiveTest
 * @dev Comprehensive Base mainnet fork test that deploys our own StakingToken contract
 */
contract StakingForkComprehensiveCleanTest is Test {
    // Deployed contract addresses on Base mainnet
    IERC20 constant OLAS_TOKEN = IERC20(0x54330d28ca3357F294334BDC454a032e7f353416);
    IServiceRegistry constant SERVICE_REGISTRY = IServiceRegistry(0x3C1fF68f5aa342D296d4DEe4Bb1cACCA912D95fE);
    IActivityChecker constant ACTIVITY_CHECKER = IActivityChecker(0x747262cC12524C571e08faCb6E6994EF2E3B97ab);
    
    // Our deployed StakingToken instance
    StakingToken public stakingToken;
    
    // Test accounts
    address public user = makeAddr("user");
    address public multisig = makeAddr("multisig");
    address public rewardFunder = makeAddr("rewardFunder");
    address public olasWhale = 0x7659CE147D0e714454073a5dd7003544234b6Aa0;
    
    // Test variables
    uint256 public serviceId;
    
    // Staking parameters for testing
    uint256 constant MIN_DEPOSIT = 10e18;           // 10 OLAS
    uint256 constant REWARDS_PER_SECOND = 1e15;    // 0.001 OLAS/second
    uint256 constant LIVENESS_PERIOD = 300;        // 5 minutes
    uint256 constant MIN_STAKING_PERIODS = 1;      // 1 period minimum
    uint256 constant MAX_INACTIVITY_PERIODS = 2;   // Allow 2 inactive periods
    uint256 constant TIME_FOR_EMISSIONS = 3600;    // 1 hour of emissions
    uint256 constant MAX_SERVICES = 5;              // Allow 5 services
    
    // Test funding amounts
    uint256 constant USER_FUNDING = 50e18;         // 50 OLAS per user
    uint256 constant REWARD_FUNDING = 100e18;      // 100 OLAS for rewards

    /**
     * @dev Set up the comprehensive test environment
     */
    function setUp() public {
        // Create Base mainnet fork
        string memory rpcUrl = vm.envOr("BASE_RPC_URL", string("https://mainnet.base.org"));
        vm.createFork(rpcUrl);
        
        console.log("Base mainnet fork created");
        
        // Fund test accounts with OLAS
        _fundTestAccounts();
        
        // Deploy our StakingToken contract
        _deployStakingToken();
        
        // Fund staking contract with rewards
        _fundStakingRewards();
        
        // Create a test service
        serviceId = 1; // Use fallback service ID for testing
        
        console.log("Setup completed successfully");
        console.log("StakingToken deployed at:", address(stakingToken));
    }

    /**
     * @dev Test 1: Validate contract deployment and initialization
     */
    function test_01_DeploymentValidation() public view {
        console.log("=== Test 1: Deployment Validation ===");
        
        // Validate all parameters are set correctly and non-zero
        assertEq(stakingToken.stakingToken(), address(OLAS_TOKEN), "Staking token should be OLAS");
        assertEq(stakingToken.serviceRegistry(), address(SERVICE_REGISTRY), "Service registry should match");
        assertEq(stakingToken.activityChecker(), address(ACTIVITY_CHECKER), "Activity checker should match");
        
        // Validate staking parameters
        assertEq(stakingToken.minStakingDeposit(), MIN_DEPOSIT, "Min deposit should match");
        assertEq(stakingToken.rewardsPerSecond(), REWARDS_PER_SECOND, "Rewards per second should match");
        assertEq(stakingToken.livenessPeriod(), LIVENESS_PERIOD, "Liveness period should match");
        assertEq(stakingToken.maxNumServices(), MAX_SERVICES, "Max services should match");
        assertEq(stakingToken.minNumStakingPeriods(), MIN_STAKING_PERIODS, "Min staking periods should match");
        assertEq(stakingToken.maxNumInactivityPeriods(), MAX_INACTIVITY_PERIODS, "Max inactivity periods should match");
        assertEq(stakingToken.timeForEmissions(), TIME_FOR_EMISSIONS, "Time for emissions should match");
        
        // Validate initial state
        assertTrue(stakingToken.stakingStarted(), "Staking should be started");
        assertEq(stakingToken.epochCounter(), 0, "Epoch counter should start at 0");
        assertGt(stakingToken.availableRewards(), 0, "Should have available rewards");
        
        console.log("All deployment parameters validated");
        console.log("Initial state is correct");
        console.log("Available rewards:", stakingToken.availableRewards());
    }

    /**
     * @dev Test 2: Basic staking and unstaking flow
     */
    function test_02_BasicStakeUnstakeFlow() public {
        console.log("=== Test 2: Basic Staking Flow ===");
        
        uint256 initialBalance = OLAS_TOKEN.balanceOf(user);
        console.log("User initial balance:", initialBalance);
        
        // Approve and stake
        vm.prank(user);
        OLAS_TOKEN.approve(address(stakingToken), MIN_DEPOSIT);
        
        vm.prank(user);
        stakingToken.stake(serviceId);
        
        // Validate staking state
        (address multisigAddr, address owner, uint32 nonces, uint256 tsStart, uint256 reward, uint256 inactivity) = 
            stakingToken.getServiceInfo(serviceId);
            
        assertEq(multisigAddr, multisig, "Multisig should match");
        assertEq(owner, user, "Owner should match");
        assertGt(tsStart, 0, "Start timestamp should be set");
        assertEq(reward, 0, "Initial reward should be 0");
        assertEq(inactivity, 0, "Initial inactivity should be 0");
        
        console.log("Service staked successfully");
        console.log("Staking timestamp:", tsStart);
        
        // Advance time to meet minimum staking period
        vm.warp(block.timestamp + LIVENESS_PERIOD * (MIN_STAKING_PERIODS + 1));
        
        // Run a checkpoint to accumulate some rewards
        (uint256[] memory serviceIds, uint256[][] memory multisigNonces, uint256[] memory rewards, uint256 epochCounter) = 
            stakingToken.checkpoint();
            
        console.log("Checkpoint completed:");
        console.log("  Epoch:", epochCounter);
        console.log("  Services processed:", serviceIds.length);
        
        // Calculate expected reward
        uint256 expectedReward = stakingToken.calculateServiceStakingReward(serviceId);
        console.log("Expected reward before unstake:", expectedReward);
        
        // Unstake and verify
        vm.prank(user);
        uint256 actualReward = stakingToken.unstake(serviceId);
        
        console.log("Service unstaked successfully");
        console.log("Actual reward:", actualReward);
        
        // Verify final state
        uint256 finalBalance = OLAS_TOKEN.balanceOf(user);
        assertGe(finalBalance, initialBalance, "Should receive deposit back plus rewards");
        
        console.log("Final balance:", finalBalance);
        console.log("Net gain:", finalBalance - initialBalance);
    }

    /**
     * @dev Test 3: Minimum deposit validation
     */
    function test_03_MinimumDepositValidation() public {
        console.log("=== Test 3: Minimum Deposit Validation ===");
        
        // Try with insufficient deposit (should fail due to transferFrom failure)
        vm.prank(user);
        OLAS_TOKEN.approve(address(stakingToken), MIN_DEPOSIT - 1);
        
        vm.expectRevert();
        vm.prank(user);
        stakingToken.stake(serviceId);
        
        console.log("Correctly rejected insufficient deposit");
        
        // Try with exact minimum
        vm.prank(user);
        OLAS_TOKEN.approve(address(stakingToken), MIN_DEPOSIT);
        
        vm.prank(user);
        stakingToken.stake(serviceId);
        
        console.log("Accepted exact minimum deposit");
        
        // Clean up
        vm.warp(block.timestamp + LIVENESS_PERIOD * (MIN_STAKING_PERIODS + 1));
        vm.prank(user);
        stakingToken.unstake(serviceId);
    }

    /**
     * @dev Test 4: Early unstaking prevention
     */
    function test_04_EarlyUnstakingPrevention() public {
        console.log("=== Test 4: Early Unstaking Prevention ===");
        
        // Stake service
        vm.prank(user);
        OLAS_TOKEN.approve(address(stakingToken), MIN_DEPOSIT);
        vm.prank(user);
        stakingToken.stake(serviceId);
        
        // Try immediate unstaking (should fail)
        vm.expectRevert();
        vm.prank(user);
        stakingToken.unstake(serviceId);
        
        console.log("Prevented immediate unstaking");
        
        // Wait sufficient time
        vm.warp(block.timestamp + LIVENESS_PERIOD * MIN_STAKING_PERIODS);
        vm.prank(user);
        stakingToken.unstake(serviceId);
        
        console.log("Allowed unstaking after minimum period");
    }

    /**
     * @dev Test 5: Multiple checkpoint cycles
     */
    function test_05_MultipleCheckpointCycles() public {
        console.log("=== Test 5: Multiple Checkpoint Cycles ===");
        
        // Stake service
        vm.prank(user);
        OLAS_TOKEN.approve(address(stakingToken), MIN_DEPOSIT);
        vm.prank(user);
        stakingToken.stake(serviceId);
        
        // Run multiple checkpoint cycles
        for (uint256 i = 0; i < 3; i++) {
            vm.warp(block.timestamp + LIVENESS_PERIOD);
            
            (uint256[] memory serviceIds, uint256[][] memory nonces, uint256[] memory rewards, uint256 epochCounter) = 
                stakingToken.checkpoint();
                
            console.log("Checkpoint", i + 1, "completed:");
            console.log("  Epoch:", epochCounter);
            console.log("  Services processed:", serviceIds.length);
        }
        
        // Check accumulated rewards
        uint256 finalReward = stakingToken.calculateServiceStakingReward(serviceId);
        console.log("Final accumulated reward:", finalReward);
        assertGt(finalReward, 0, "Should have accumulated rewards");
        
        // Clean up
        vm.warp(block.timestamp + LIVENESS_PERIOD * MIN_STAKING_PERIODS);
        vm.prank(user);
        uint256 actualReward = stakingToken.unstake(serviceId);
        console.log("Unstaked with reward:", actualReward);
    }

    // --- Helper Functions ---

    /**
     * @dev Fund test accounts with OLAS tokens
     */
    function _fundTestAccounts() internal {
        console.log("Funding test accounts...");
        
        // Deal tokens directly for testing
        deal(address(OLAS_TOKEN), user, USER_FUNDING);
        deal(address(OLAS_TOKEN), rewardFunder, REWARD_FUNDING);
        
        console.log("Test accounts funded");
        console.log("User balance:", OLAS_TOKEN.balanceOf(user));
        console.log("Reward funder balance:", OLAS_TOKEN.balanceOf(rewardFunder));
    }

    /**
     * @dev Deploy StakingToken with test parameters
     */
    function _deployStakingToken() internal {
        console.log("Deploying StakingToken...");
        
        // Create staking parameters
        StakingParams memory params = StakingParams({
            metadataHash: bytes32("test-quorum-staking"),
            maxNumServices: MAX_SERVICES,
            rewardsPerSecond: REWARDS_PER_SECOND,
            minStakingDeposit: MIN_DEPOSIT,
            minNumStakingPeriods: MIN_STAKING_PERIODS,
            maxNumInactivityPeriods: MAX_INACTIVITY_PERIODS,
            livenessPeriod: LIVENESS_PERIOD,
            timeForEmissions: TIME_FOR_EMISSIONS,
            numAgentInstances: 1,
            agentIds: new uint32[](0),           // No specific agent requirements
            threshold: 0,                        // No threshold requirement
            configHash: bytes32(0),              // No config hash requirement
            proxyHash: bytes32(0),               // No proxy hash requirement for testing
            serviceRegistry: address(SERVICE_REGISTRY),
            activityChecker: address(ACTIVITY_CHECKER)
        });
        
        // Deploy StakingToken
        stakingToken = new StakingToken(address(OLAS_TOKEN), params);
        
        console.log("StakingToken deployed successfully");
        console.log("Contract address:", address(stakingToken));
    }

    /**
     * @dev Fund staking contract with reward tokens
     */
    function _fundStakingRewards() internal {
        console.log("Funding staking rewards...");
        
        vm.prank(rewardFunder);
        OLAS_TOKEN.approve(address(stakingToken), REWARD_FUNDING);
        
        vm.prank(rewardFunder);
        stakingToken.fundRewards(REWARD_FUNDING);
        
        console.log("Staking rewards funded");
        console.log("Amount:", REWARD_FUNDING);
        console.log("Available rewards:", stakingToken.availableRewards());
    }
}
