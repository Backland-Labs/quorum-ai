// SPDX-License-Identifier: MIT
pragma solidity 0.8.24;

import {Test, console} from "forge-std/Test.sol";

// Interfaces for deployed contracts
interface IStakingToken {
    function stake(uint256 serviceId) external;
    function isServiceStaked(uint256 serviceId) external view returns (bool);
    function getServiceInfo(uint256 serviceId) external view returns (address, address, uint32, uint256, uint256, uint256);
    function minStakingDeposit() external view returns (uint256);
    function serviceRegistry() external view returns (address);
    function stakingStarted() external view returns (bool);
}

interface IERC20 {
    function approve(address spender, uint256 amount) external returns (bool);
    function balanceOf(address account) external view returns (uint256);
}

interface IServiceRegistry {
    function exists(uint256 serviceId) external view returns (bool);
    function ownerOf(uint256 serviceId) external view returns (address);
    function getService(uint256 serviceId) external view returns (
        address serviceOwner,
        bytes32 configHash,
        bytes32 proxyHash,
        uint32[] memory agentIds,
        uint32[] memory slots,
        uint32[] memory bonds,
        uint32 threshold
    );
    function getServiceState(uint256 serviceId) external view returns (uint8);
    function mapServiceIdSetOfMultisigs(uint256 serviceId, uint256 index) external view returns (address);
}

/**
 * @title ProductionValidationTest
 * @dev Test to identify specific validation issues preventing service staking
 */
contract ProductionValidationTest is Test {
    IERC20 constant OLAS_TOKEN = IERC20(0x54330d28ca3357F294334BDC454a032e7f353416);
    IStakingToken public stakingToken = IStakingToken(0x93740A233f424B5d07C0B129D28DEdE378784cfb);
    IServiceRegistry public serviceRegistry;
    
    function setUp() public {
        vm.createFork("https://mainnet.base.org");
        serviceRegistry = IServiceRegistry(stakingToken.serviceRegistry());
        console.log("=== PRODUCTION VALIDATION TEST ===");
    }

    /**
     * @dev Test specific service details to understand validation requirements
     */
    function test_ServiceValidationDetails() public {
        console.log("=== Service Validation Analysis ===");
        
        // Test service 1 in detail
        uint256 testServiceId = 1;
        
        console.log("Analyzing service", testServiceId);
        
        // Check basic existence
        bool exists = serviceRegistry.exists(testServiceId);
        console.log("Service exists:", exists);
        
        if (!exists) {
            console.log("Service does not exist, cannot analyze");
            return;
        }
        
        // Get owner
        address owner = serviceRegistry.ownerOf(testServiceId);
        console.log("Service owner:", owner);
        
        // Try to get service state
        try serviceRegistry.getServiceState(testServiceId) returns (uint8 state) {
            console.log("Service state:", state);
            console.log("State meanings: 0=NonExistent, 1=PreRegistration, 2=ActiveRegistration, 3=FinishedRegistration, 4=Deployed, 5=TerminatedBonded");
        } catch Error(string memory reason) {
            console.log("Failed to get service state:", reason);
        } catch {
            console.log("Failed to get service state (unknown error)");
        }
        
        // Try to get service details
        try serviceRegistry.getService(testServiceId) returns (
            address serviceOwner,
            bytes32 configHash,
            bytes32 proxyHash,
            uint32[] memory agentIds,
            uint32[] memory slots,
            uint32[] memory bonds,
            uint32 threshold
        ) {
            console.log("Service details retrieved:");
            console.log("  Owner:", serviceOwner);
            console.log("  Config hash:", uint256(configHash));
            console.log("  Proxy hash:", uint256(proxyHash));
            console.log("  Agent IDs count:", agentIds.length);
            console.log("  Threshold:", threshold);
            
            if (agentIds.length > 0) {
                console.log("  First agent ID:", agentIds[0]);
            }
            
        } catch Error(string memory reason) {
            console.log("Failed to get service details:", reason);
        } catch {
            console.log("Failed to get service details (unknown error)");
        }
        
        // Try to get multisig address
        try serviceRegistry.mapServiceIdSetOfMultisigs(testServiceId, 0) returns (address multisig) {
            console.log("Service multisig:", multisig);
        } catch Error(string memory reason) {
            console.log("Failed to get multisig:", reason);
        } catch {
            console.log("Failed to get multisig (unknown error)");
        }
    }

    /**
     * @dev Test the exact staking call to capture the specific error
     */
    function test_DetailedStakingAttempt() public {
        console.log("=== Detailed Staking Attempt ===");
        
        uint256 testServiceId = 1;
        address owner = serviceRegistry.ownerOf(testServiceId);
        uint256 minDeposit = stakingToken.minStakingDeposit();
        
        console.log("Attempting detailed staking analysis for service", testServiceId);
        console.log("Service owner:", owner);
        console.log("Required deposit:", minDeposit);
        
        // Fund the owner
        deal(address(OLAS_TOKEN), owner, 100e18);
        
        // Check staking contract state
        console.log("Staking started:", stakingToken.stakingStarted());
        
        // Approve tokens
        vm.prank(owner);
        OLAS_TOKEN.approve(address(stakingToken), minDeposit);
        console.log("Tokens approved");
        
        // Check if service is already staked
        try stakingToken.isServiceStaked(testServiceId) returns (bool isStaked) {
            console.log("Service already staked:", isStaked);
            if (isStaked) {
                console.log("Service is already staked, cannot stake again");
                return;
            }
        } catch Error(string memory reason) {
            console.log("Could not check if service is staked:", reason);
        } catch {
            console.log("Could not check staking status (unknown error)");
        }
        
        // Attempt to stake with detailed error capture
        vm.prank(owner);
        try stakingToken.stake(testServiceId) {
            console.log("SUCCESS: Service staked successfully!");
            
            // Verify staking
            try stakingToken.isServiceStaked(testServiceId) returns (bool nowStaked) {
                console.log("Service now staked:", nowStaked);
            } catch {
                console.log("Could not verify staking after success");
            }
            
        } catch Error(string memory reason) {
            console.log("STAKING FAILED with reason:", reason);
            
            // Analyze the specific error
            if (bytes(reason).length == 0) {
                console.log("Empty error message - likely a validation check failed");
            } else {
                console.log("Specific error provided");
            }
            
        } catch (bytes memory lowLevelData) {
            console.log("STAKING FAILED with low-level error");
            console.log("Error data length:", lowLevelData.length);
            
            if (lowLevelData.length >= 4) {
                // Try to decode the error selector
                bytes4 errorSelector;
                assembly {
                    errorSelector := mload(add(lowLevelData, 0x20))
                }
                console.log("Error selector:");
                console.logBytes4(errorSelector);
            }
        }
    }

    /**
     * @dev Test multiple services to find patterns in failures
     */
    function test_MultipleServiceAnalysis() public {
        console.log("=== Multiple Service Analysis ===");
        
        for (uint256 i = 1; i <= 5; i++) {
            console.log("\n--- Analyzing Service", i, "---");
            
            if (!serviceRegistry.exists(i)) {
                console.log("Service", i, "does not exist");
                continue;
            }
            
            address owner = serviceRegistry.ownerOf(i);
            console.log("Owner:", owner);
            
            // Check service state
            try serviceRegistry.getServiceState(i) returns (uint8 state) {
                console.log("State:", state);
                
                if (state == 4) { // DEPLOYED
                    console.log("Service is DEPLOYED - should be stakeable");
                    
                    // Try a quick staking test
                    deal(address(OLAS_TOKEN), owner, 100e18);
                    vm.prank(owner);
                    OLAS_TOKEN.approve(address(stakingToken), stakingToken.minStakingDeposit());
                    
                    vm.prank(owner);
                    try stakingToken.stake(i) {
                        console.log("SUCCESS: Service", i, "staked!");
                        
                        // Check if we can get service info
                        try stakingToken.getServiceInfo(i) returns (
                            address multisigAddr,
                            address serviceOwner,
                            uint32 nonces,
                            uint256 tsStart,
                            uint256 reward,
                            uint256 inactivity
                        ) {
                            console.log("Service info retrieved after staking:");
                            console.log("  Multisig:", multisigAddr);
                            console.log("  Owner:", serviceOwner);
                            console.log("  Start time:", tsStart);
                        } catch {
                            console.log("Could not get service info after staking");
                        }
                        
                    } catch Error(string memory reason) {
                        console.log("FAILED to stake service", i, ":", reason);
                    } catch {
                        console.log("FAILED to stake service", i, "(unknown error)");
                    }
                } else {
                    console.log("Service not in DEPLOYED state");
                }
            } catch {
                console.log("Could not get service state");
            }
        }
    }
}