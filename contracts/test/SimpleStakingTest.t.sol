// SPDX-License-Identifier: MIT
pragma solidity 0.8.24;

import {Test, console} from "forge-std/Test.sol";

/**
 * @title SimpleStakingTest
 * @dev Simple test to validate our deployed StakingToken works correctly
 */
contract SimpleStakingTest is Test {
    
    // Our deployed StakingToken address (latest deployment)
    address constant STAKING_TOKEN = 0x93740A233f424B5d07C0B129D28DEdE378784cfb;
    address constant OLAS_TOKEN = 0x54330d28ca3357F294334BDC454a032e7f353416;
    address constant SERVICE_REGISTRY = 0x3C1fF68f5aa342D296d4DEe4Bb1cACCA912D95fE;
    address constant ACTIVITY_CHECKER = 0x747262cC12524C571e08faCb6E6994EF2E3B97ab;
    
    // OLAS whale for funding
    address constant OLAS_WHALE = 0x7659CE147D0e714454073a5dd7003544234b6Aa0;
    
    function setUp() public {
        // We're already on the fork, no need to create it
        console.log("Testing deployed StakingToken at:", STAKING_TOKEN);
    }
    
    /**
     * @dev Test basic contract configuration
     */
    function test_BasicConfiguration() public {
        console.log("=== Testing Basic Configuration ===");
        
        // Test configuration calls
        (bool success, bytes memory data) = STAKING_TOKEN.staticcall(
            abi.encodeWithSignature("serviceRegistry()")
        );
        require(success, "serviceRegistry call failed");
        address serviceRegistry = abi.decode(data, (address));
        assertEq(serviceRegistry, SERVICE_REGISTRY, "Service registry mismatch");
        console.log("Service Registry OK:", serviceRegistry);
        
        // Test activity checker
        (success, data) = STAKING_TOKEN.staticcall(
            abi.encodeWithSignature("activityChecker()")
        );
        require(success, "activityChecker call failed");
        address activityChecker = abi.decode(data, (address));
        assertEq(activityChecker, ACTIVITY_CHECKER, "Activity checker mismatch");
        console.log("Activity Checker OK:", activityChecker);
        
        // Test staking token
        (success, data) = STAKING_TOKEN.staticcall(
            abi.encodeWithSignature("stakingToken()")
        );
        require(success, "stakingToken call failed");
        address stakingToken = abi.decode(data, (address));
        assertEq(stakingToken, OLAS_TOKEN, "Staking token mismatch");
        console.log("Staking Token OK:", stakingToken);
        
        // Test parameters
        (success, data) = STAKING_TOKEN.staticcall(
            abi.encodeWithSignature("minStakingDeposit()")
        );
        require(success, "minStakingDeposit call failed");
        uint256 minDeposit = abi.decode(data, (uint256));
        assertEq(minDeposit, 10 ether, "Min deposit should be 10 OLAS");
        console.log("Min Staking Deposit OK:", minDeposit);
        
        (success, data) = STAKING_TOKEN.staticcall(
            abi.encodeWithSignature("maxNumServices()")
        );
        require(success, "maxNumServices call failed");
        uint256 maxServices = abi.decode(data, (uint256));
        assertEq(maxServices, 2, "Max services should be 2");
        console.log("Max Services OK:", maxServices);
        
        (success, data) = STAKING_TOKEN.staticcall(
            abi.encodeWithSignature("rewardsPerSecond()")
        );
        require(success, "rewardsPerSecond call failed");
        uint256 rewardsPerSecond = abi.decode(data, (uint256));
        assertEq(rewardsPerSecond, 824652777778, "Rewards per second mismatch");
        console.log("Rewards Per Second OK:", rewardsPerSecond);
    }
    
    /**
     * @dev Test OLAS token interaction
     */
    function test_OLASTokenInteraction() public {
        console.log("=== Testing OLAS Token Interaction ===");
        
        // Check OLAS whale balance
        (bool success, bytes memory data) = OLAS_TOKEN.staticcall(
            abi.encodeWithSignature("balanceOf(address)", OLAS_WHALE)
        );
        require(success, "OLAS balanceOf call failed");
        uint256 whaleBalance = abi.decode(data, (uint256));
        console.log("OLAS Whale Balance:", whaleBalance);
        assertGt(whaleBalance, 100 ether, "Whale should have plenty of OLAS");
        
        // Test token transfer (simulate funding)
        vm.startPrank(OLAS_WHALE);
        
        address testUser = makeAddr("testUser");
        
        // Transfer OLAS to test user
        (success, ) = OLAS_TOKEN.call(
            abi.encodeWithSignature("transfer(address,uint256)", testUser, 50 ether)
        );
        require(success, "OLAS transfer failed");
        
        vm.stopPrank();
        
        // Verify transfer
        (success, data) = OLAS_TOKEN.staticcall(
            abi.encodeWithSignature("balanceOf(address)", testUser)
        );
        require(success, "balanceOf call failed");
        uint256 userBalance = abi.decode(data, (uint256));
        assertEq(userBalance, 50 ether, "User should have 50 OLAS");
        console.log("OK Test user funded with:", userBalance);
    }
    
    /**
     * @dev Test service registry interaction
     */
    function test_ServiceRegistryInteraction() public {
        console.log("=== Testing Service Registry Interaction ===");
        
        // Check if service ID 1 exists
        (bool success, bytes memory data) = SERVICE_REGISTRY.staticcall(
            abi.encodeWithSignature("exists(uint256)", 1)
        );
        require(success, "Service registry exists call failed");
        bool serviceExists = abi.decode(data, (bool));
        console.log("Service ID 1 exists:", serviceExists);
        
        if (serviceExists) {
            // Get service info
            (success, data) = SERVICE_REGISTRY.staticcall(
                abi.encodeWithSignature("getService(uint256)", 1)
            );
            require(success, "getService call failed");
            console.log("OK Service registry responsive");
        } else {
            console.log("OK Service registry responsive (no service 1)");
        }
    }
    
    /**
     * @dev Test activity checker interaction
     */
    function test_ActivityCheckerInteraction() public {
        console.log("=== Testing Activity Checker Interaction ===");
        
        address testMultisig = makeAddr("testMultisig");
        
        // Test getMultisigNonces
        (bool success, bytes memory data) = ACTIVITY_CHECKER.staticcall(
            abi.encodeWithSignature("getMultisigNonces(address)", testMultisig)
        );
        require(success, "getMultisigNonces call failed");
        uint256[] memory nonces = abi.decode(data, (uint256[]));
        console.log("OK Activity checker responsive, nonces length:", nonces.length);
        
        if (nonces.length > 0) {
            console.log("First nonce value:", nonces[0]);
        }
    }
    
    /**
     * @dev Test current staking state
     */
    function test_StakingState() public {
        console.log("=== Testing Current Staking State ===");
        
        // Get service IDs
        (bool success, bytes memory data) = STAKING_TOKEN.staticcall(
            abi.encodeWithSignature("getServiceIds()")
        );
        require(success, "getServiceIds call failed");
        uint256[] memory serviceIds = abi.decode(data, (uint256[]));
        console.log("OK Current staked services count:", serviceIds.length);
        
        // Get token balance
        (success, data) = STAKING_TOKEN.staticcall(
            abi.encodeWithSignature("getTokenBalance()")
        );
        require(success, "getTokenBalance call failed");
        uint256 tokenBalance = abi.decode(data, (uint256));
        console.log("OK Contract token balance:", tokenBalance);
        
        console.log("=== All Tests Passed! ===");
    }
}