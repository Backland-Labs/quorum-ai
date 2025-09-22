// SPDX-License-Identifier: MIT
pragma solidity 0.8.24;

import {Script, console} from "forge-std/Script.sol";
import {StakingToken} from "../src/StakingToken.sol";
import {StakingParams} from "../src/StakingBase.sol";

/**
 * @title DeployOurStakingTokenScript
 * @dev Deployment script for our own StakingToken implementation.
 * This deploys the StakingToken from our src/ directory with proper initialization.
 */
contract DeployOurStakingTokenScript is Script {
    
    // Base mainnet addresses
    address constant SERVICE_REGISTRY = 0x3C1fF68f5aa342D296d4DEe4Bb1cACCA912D95fE;
    address constant ACTIVITY_CHECKER = 0x747262cC12524C571e08faCb6E6994EF2E3B97ab;
    address constant OLAS_TOKEN = 0x54330d28ca3357F294334BDC454a032e7f353416;
    
    /**
     * @notice Main deployment function.
     * @dev Deploys our StakingToken with production-like parameters.
     */
    function run() public returns (StakingToken stakingToken) {
        uint256 deployerPrivateKey = vm.envUint("PRIVATE_KEY");
        address deployer = vm.addr(deployerPrivateKey);
        
        console.log("=== Our StakingToken Deployment ===");
        console.log("Deployer:", deployer);
        console.log("Service Registry:", SERVICE_REGISTRY);
        console.log("Activity Checker:", ACTIVITY_CHECKER);
        console.log("OLAS Token:", OLAS_TOKEN);
        
        // Prepare staking parameters matching production values
        uint32[] memory agentIds = new uint32[](0); // No specific agent requirements
        
        StakingParams memory stakingParams = StakingParams({
            metadataHash: keccak256("QuorumAI Local Test StakingToken"),
            maxNumServices: 2,                          // Max 2 services can stake
            rewardsPerSecond: 824652777778,             // ~2.13 OLAS/month per service
            minStakingDeposit: 10 ether,                // 10 OLAS minimum deposit  
            minNumStakingPeriods: 3,                    // Min 3 periods before unstaking
            maxNumInactivityPeriods: 2,                 // Evicted after 2 inactive periods
            livenessPeriod: 86400,                      // 24 hour activity check window
            timeForEmissions: 2592000,                  // 30 day emission period
            numAgentInstances: 1,                       // 1 agent instance per service
            agentIds: agentIds,                         // No specific agent requirements
            threshold: 1,                               // Multisig threshold of 1
            configHash: bytes32(0),                     // No specific config hash required
            proxyHash: bytes32(0),                      // No specific proxy hash required
            serviceRegistry: SERVICE_REGISTRY,
            activityChecker: ACTIVITY_CHECKER
        });
        
        console.log("=== Staking Parameters ===");
        console.log("Max Services:", stakingParams.maxNumServices);
        console.log("Rewards Per Second:", stakingParams.rewardsPerSecond);
        console.log("Min Staking Deposit:", stakingParams.minStakingDeposit);
        console.log("Liveness Period:", stakingParams.livenessPeriod);
        
        vm.startBroadcast(deployerPrivateKey);
        
        // Deploy our StakingToken contract
        stakingToken = new StakingToken(OLAS_TOKEN, stakingParams);
        
        vm.stopBroadcast();
        
        // Log deployment information
        console.log("=== Deployment Results ===");
        console.log("StakingToken deployed to:", address(stakingToken));
        console.log("Deployment successful!");
        
        // Verify deployment
        require(address(stakingToken) != address(0), "Deployment failed");
        require(stakingToken.serviceRegistry() == SERVICE_REGISTRY, "Service Registry not set correctly");
        require(stakingToken.activityChecker() == ACTIVITY_CHECKER, "Activity Checker not set correctly");
        require(stakingToken.stakingToken() == OLAS_TOKEN, "Staking token not set correctly");
        
        console.log("=== Deployment Verification ===");
        console.log("Service Registry verified:", stakingToken.serviceRegistry());
        console.log("Activity Checker verified:", stakingToken.activityChecker());
        console.log("Staking Token verified:", stakingToken.stakingToken());
        console.log("Min Staking Deposit:", stakingToken.minStakingDeposit());
        console.log("Max Num Services:", stakingToken.maxNumServices());
        console.log("Rewards Per Second:", stakingToken.rewardsPerSecond());
        console.log("Liveness Period:", stakingToken.livenessPeriod());
        
        // Test state queries
        console.log("=== Contract State ===");
        console.log("Token Balance:", stakingToken.getTokenBalance());
        uint256[] memory serviceIds = stakingToken.getServiceIds();
        console.log("Number of Services:", serviceIds.length);
        
        return stakingToken;
    }
}