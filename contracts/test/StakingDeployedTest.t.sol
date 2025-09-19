// SPDX-License-Identifier: MIT
pragma solidity 0.8.24;

import {Test, console} from "forge-std/Test.sol";

/**
 * @title StakingDeployedTest
 * @dev Complete test suite for our deployed StakingToken with proper error analysis
 */
contract StakingDeployedTest is Test {
    
    // Contract addresses
    address constant STAKING_TOKEN = 0x93740A233f424B5d07C0B129D28DEdE378784cfb;
    address constant OLAS_TOKEN = 0x54330d28ca3357F294334BDC454a032e7f353416;
    address constant SERVICE_REGISTRY = 0x3C1fF68f5aa342D296d4DEe4Bb1cACCA912D95fE;
    address constant ACTIVITY_CHECKER = 0x747262cC12524C571e08faCb6E6994EF2E3B97ab;
    address constant ATTESTATION_TRACKER = 0x9BC8c713a159a028aC5590ffE42DaF0d9A6467AC;
    
    // Actual deployed multisig from Service Registry Service ID 1
    address constant REAL_MULTISIG = 0x1B04Eedcdfe4F9DeE112aBAE519b521C5a891Ba6;
    
    // Test accounts
    address public testUser;
    address public serviceOwner;
    
    function setUp() public {
        testUser = makeAddr("testUser");
        serviceOwner = makeAddr("serviceOwner");
        
        console.log("=== Setup Complete ===");
        console.log("StakingToken:", STAKING_TOKEN);
        console.log("Real Multisig:", REAL_MULTISIG);
        console.log("Test User:", testUser);
    }
    
    /**
     * @dev Test 1: Basic Configuration (should pass)
     */
    function test_01_BasicConfiguration() public view {
        console.log("=== Test 1: Basic Configuration ===");
        
        (bool success, bytes memory data) = STAKING_TOKEN.staticcall(
            abi.encodeWithSignature("serviceRegistry()")
        );
        require(success, "serviceRegistry call failed");
        address serviceRegistry = abi.decode(data, (address));
        assertEq(serviceRegistry, SERVICE_REGISTRY);
        
        (success, data) = STAKING_TOKEN.staticcall(
            abi.encodeWithSignature("minStakingDeposit()")
        );
        require(success, "minStakingDeposit call failed");
        uint256 minDeposit = abi.decode(data, (uint256));
        assertEq(minDeposit, 10 ether);
        
        console.log("Configuration OK - Min Deposit:", minDeposit);
    }
    
    /**
     * @dev Test 2: Activity Checker with Real Multisig (should pass)
     */
    function test_02_ActivityCheckerWithRealMultisig() public {
        console.log("=== Test 2: Activity Checker with Real Multisig ===");
        
        // Test with actual deployed multisig
        (bool success, bytes memory data) = ACTIVITY_CHECKER.staticcall(
            abi.encodeWithSignature("getMultisigNonces(address)", REAL_MULTISIG)
        );
        require(success, "getMultisigNonces with real multisig failed");
        uint256[] memory nonces = abi.decode(data, (uint256[]));
        
        assertEq(nonces.length, 4, "Should return 4 nonces");
        console.log("Real Multisig Nonces:");
        console.log("- Multisig nonce:", nonces[0]);
        console.log("- Casted votes:", nonces[1]);
        console.log("- Voting opportunities:", nonces[2]);
        console.log("- No voting opportunities:", nonces[3]);
        
        // Verify multisig has a nonce (should be > 0 for real multisig)
        assertGt(nonces[0], 0, "Real multisig should have nonce > 0");
    }
    
    /**
     * @dev Test 3: Activity Checker with Test Address (should fail with explanation)
     */
    function test_03_ActivityCheckerWithTestAddress() public {
        console.log("=== Test 3: Activity Checker with Test Address (Expected Failure) ===");
        
        address testAddr = makeAddr("testMultisig");
        console.log("Testing with test address:", testAddr);
        
        // Check if address has contract code
        uint256 codeSize;
        assembly {
            codeSize := extcodesize(testAddr)
        }
        console.log("Code size at test address:", codeSize);
        assertEq(codeSize, 0, "Test address should have no code");
        
        // This should fail because test address has no nonce() function
        (bool success, ) = ACTIVITY_CHECKER.staticcall(
            abi.encodeWithSignature("getMultisigNonces(address)", testAddr)
        );
        assertFalse(success, "Call should fail for test address");
        console.log("Expected failure confirmed: Test address has no contract code");
    }
    
    /**
     * @dev Test 4: OLAS Token Funding Strategy
     */
    function test_04_OLASTokenFunding() public {
        console.log("=== Test 4: OLAS Token Funding Strategy ===");
        
        // Check total supply
        (bool success, bytes memory data) = OLAS_TOKEN.staticcall(
            abi.encodeWithSignature("totalSupply()")
        );
        require(success, "totalSupply call failed");
        uint256 totalSupply = abi.decode(data, (uint256));
        console.log("OLAS Total Supply:", totalSupply);
        assertGt(totalSupply, 0, "OLAS should have supply");
        
        // Try to find OLAS by using anvil deal cheatcode
        vm.deal(testUser, 100 ether); // Give ETH for gas
        
        // Use anvil cheatcode to give OLAS tokens
        deal(OLAS_TOKEN, testUser, 50 ether);
        
        // Verify funding worked
        (success, data) = OLAS_TOKEN.staticcall(
            abi.encodeWithSignature("balanceOf(address)", testUser)
        );
        require(success, "balanceOf call failed");
        uint256 balance = abi.decode(data, (uint256));
        console.log("Test user OLAS balance after deal:", balance);
        assertEq(balance, 50 ether, "Deal should give exactly 50 OLAS");
    }
}
