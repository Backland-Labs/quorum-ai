// SPDX-License-Identifier: MIT
pragma solidity 0.8.24;

import {Script, console} from "forge-std/Script.sol";

// Minimal interface for StakingFactory
interface IStakingFactory {
    function createStakingInstance(
        address implementation,
        bytes memory initPayload
    ) external returns (address);
    
    function getInstancesSize() external view returns (uint256);
    function mapInstanceParams(address instance) external view returns (address, uint256);
}

/**
 * @title DeployStakingTokenViaFactoryScript
 * @dev Uses the existing StakingFactory on Base to deploy a new StakingToken instance.
 * This approach avoids dependency issues and uses the production factory pattern.
 */
contract DeployStakingTokenViaFactoryScript is Script {
    
    // Base mainnet addresses
    address constant STAKING_FACTORY = 0x1cEe30D08943EB58EFF84DD1AB44a6ee6FEff63a;
    address constant SERVICE_REGISTRY = 0x3C1fF68f5aa342D296d4DEe4Bb1cACCA912D95fE;
    address constant ACTIVITY_CHECKER = 0x747262cC12524C571e08faCb6E6994EF2E3B97ab;
    address constant SERVICE_REGISTRY_TOKEN_UTILITY = 0x63e66d7ad413C01A7b49C7FF4e3Bb765C4E4bd1b;
    address constant OLAS_TOKEN = 0x54330d28ca3357F294334BDC454a032e7f353416;
    
    // Minimal interface for StakingToken initialization
    struct StakingParams {
        bytes32 metadataHash;
        uint256 maxNumServices;
        uint256 rewardsPerSecond;
        uint256 minStakingDeposit;
        uint256 minNumStakingPeriods;
        uint256 maxNumInactivityPeriods;
        uint256 livenessPeriod;
        uint256 timeForEmissions;
        uint256 numAgentInstances;
        uint256[] agentIds;
        uint256 threshold;
        bytes32 configHash;
        bytes32 proxyHash;
        address serviceRegistry;
        address activityChecker;
    }
    
    /**
     * @notice Main deployment function.
     * @dev Uses StakingFactory to create a new StakingToken instance.
     */
    function run() public returns (address stakingInstance) {
        uint256 deployerPrivateKey = vm.envUint("PRIVATE_KEY");
        address deployer = vm.addr(deployerPrivateKey);
        
        console.log("=== StakingToken Deployment via Factory ===");
        console.log("Deployer:", deployer);
        console.log("Factory:", STAKING_FACTORY);
        
        // Check factory state
        IStakingFactory factory = IStakingFactory(STAKING_FACTORY);
        uint256 instancesBefore = factory.getInstancesSize();
        console.log("Existing instances:", instancesBefore);
        
        // Prepare staking parameters matching production values
        StakingParams memory stakingParams = StakingParams({
            metadataHash: keccak256("QuorumAI Local Test Instance"),
            maxNumServices: 2,
            rewardsPerSecond: 824652777778,     // ~2.13 OLAS/month per service
            minStakingDeposit: 10 ether,        // 10 OLAS
            minNumStakingPeriods: 3,
            maxNumInactivityPeriods: 2,
            livenessPeriod: 86400,              // 24 hours
            timeForEmissions: 2592000,          // 30 days
            numAgentInstances: 1,
            agentIds: new uint256[](0),
            threshold: 1,
            configHash: bytes32(0),
            proxyHash: bytes32(0),
            serviceRegistry: SERVICE_REGISTRY,
            activityChecker: ACTIVITY_CHECKER
        });
        
        // Encode initialization payload
        bytes memory initPayload = abi.encodeWithSignature(
            "initialize((bytes32,uint256,uint256,uint256,uint256,uint256,uint256,uint256,uint256,uint256[],uint256,bytes32,bytes32,address,address),address,address)",
            stakingParams,
            SERVICE_REGISTRY_TOKEN_UTILITY,
            OLAS_TOKEN
        );
        
        console.log("Initialization payload size:", initPayload.length);
        
        vm.startBroadcast(deployerPrivateKey);
        
        // We need to find the StakingToken implementation address
        // For now, let's try with a zero address and see what the factory returns
        try factory.createStakingInstance(address(0), initPayload) returns (address instance) {
            stakingInstance = instance;
        } catch Error(string memory reason) {
            console.log("Factory call failed:", reason);
            revert(string(abi.encodePacked("Factory deployment failed: ", reason)));
        } catch (bytes memory) {
            console.log("Factory call failed with low-level error");
            revert("Factory deployment failed with low-level error");
        }
        
        vm.stopBroadcast();
        
        if (stakingInstance == address(0)) {
            revert("Factory returned zero address");
        }
        
        console.log("StakingToken instance created at:", stakingInstance);
        
        // Verify the deployment
        uint256 instancesAfter = factory.getInstancesSize();
        console.log("Instances after deployment:", instancesAfter);
        
        return stakingInstance;
    }
}