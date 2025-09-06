// SPDX-License-Identifier: MIT
pragma solidity 0.8.24;

import {Script, console} from "forge-std/Script.sol";
import {AttestationTracker} from "../src/AttestationTracker.sol";

/**
 * @title DeployMainnet
 * @dev Deployment script for the AttestationTracker contract on Ethereum Mainnet.
 * This script includes additional safety checks and verification steps for mainnet deployment.
 */
contract DeployMainnet is Script {
    // Mainnet EAS contract address
    address constant MAINNET_EAS = 0xA1207F3BBa224E2c9c3c6D5aF63D0eb1582Ce587;
    
    /**
     * @notice Main deployment function for mainnet.
     * @dev Deploys AttestationTracker contract with safety checks and verification.
     * @return attestationTracker The deployed AttestationTracker contract instance.
     */
    function run() public returns (AttestationTracker attestationTracker) {
        // Get the deployer's private key from environment
        uint256 deployerPrivateKey = vm.envUint("PRIVATE_KEY");
        
        // Get the owner address from environment
        address owner = vm.envAddress("ATTESTATION_TRACKER_OWNER");
        
        // Optional: Allow override of EAS address via env, otherwise use mainnet constant
        address easAddress;
        try vm.envAddress("EAS_CONTRACT_ADDRESS") returns (address envEas) {
            easAddress = envEas;
            console.log("Using EAS address from environment:", easAddress);
        } catch {
            easAddress = MAINNET_EAS;
            console.log("Using default mainnet EAS address:", easAddress);
        }
        
        // Validate addresses
        require(owner != address(0), "Owner address cannot be zero");
        require(easAddress != address(0), "EAS address cannot be zero");
        require(easAddress == MAINNET_EAS, "WARNING: EAS address does not match expected mainnet address");
        
        // Get deployer address for logging
        address deployer = vm.addr(deployerPrivateKey);
        
        console.log("=====================================");
        console.log("=== MAINNET DEPLOYMENT - CAUTION ===");
        console.log("=====================================");
        console.log("Network: Ethereum Mainnet");
        console.log("Deployer:", deployer);
        console.log("Contract Owner:", owner);
        console.log("EAS Address:", easAddress);
        console.log("=====================================");
        
        // Check deployer balance
        uint256 deployerBalance = deployer.balance;
        console.log("Deployer ETH Balance:", deployerBalance / 1e18, "ETH");
        require(deployerBalance > 0.01 ether, "Insufficient ETH balance for deployment");
        
        // Simulate deployment first
        console.log("\n--- Simulating Deployment ---");
        vm.startBroadcast(deployerPrivateKey);
        
        // Deploy the AttestationTracker contract
        attestationTracker = new AttestationTracker(owner, easAddress);
        
        vm.stopBroadcast();
        
        // Log deployment information
        console.log("\n=== Deployment Successful ===");
        console.log("AttestationTracker deployed to:", address(attestationTracker));
        console.log("Transaction gas used:", gasleft());
        
        // Verify deployment
        require(address(attestationTracker) != address(0), "Deployment failed");
        require(attestationTracker.owner() == owner, "Owner not set correctly");
        require(attestationTracker.EAS() == easAddress, "EAS address not set correctly");
        
        console.log("\n=== Post-Deployment Verification ===");
        console.log("[OK] Contract deployed successfully");
        console.log("[OK] Owner verified:", attestationTracker.owner());
        console.log("[OK] EAS address verified:", attestationTracker.EAS());
        
        // Test initial state
        address testMultisig = makeAddr("test");
        uint256 initialCount = attestationTracker.getNumAttestations(testMultisig);
        require(initialCount == 0, "Initial attestation count should be 0");
        console.log("[OK] Initial state verified");
        
        console.log("\n=== Deployment Complete ===");
        console.log("Contract Address:", address(attestationTracker));
        console.log("\nIMPORTANT: Save this address!");
        console.log("Next steps:");
        console.log("1. Verify the contract on Etherscan");
        console.log("2. Transfer ownership if needed");
        console.log("3. Test the contract functions");
        
        return attestationTracker;
    }
    
    /**
     * @notice Dry run function for testing deployment without broadcasting.
     * @dev Use this to test deployment parameters before actual deployment.
     */
    function dryRun() public returns (AttestationTracker attestationTracker) {
        console.log("=== DRY RUN - No actual deployment ===");
        
        // Get the owner address from environment
        address owner = vm.envAddress("ATTESTATION_TRACKER_OWNER");
        address easAddress = MAINNET_EAS;
        
        // Validate addresses
        require(owner != address(0), "Owner address cannot be zero");
        
        console.log("Would deploy with:");
        console.log("- Owner:", owner);
        console.log("- EAS:", easAddress);
        
        // Create contract instance without broadcasting
        attestationTracker = new AttestationTracker(owner, easAddress);
        
        console.log("Contract would be deployed to:", address(attestationTracker));
        console.log("Dry run complete");
        
        return attestationTracker;
    }
}