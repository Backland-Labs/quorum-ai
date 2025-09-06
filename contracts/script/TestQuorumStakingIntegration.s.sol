// SPDX-License-Identifier: MIT
pragma solidity 0.8.24;

import {Script, console} from "forge-std/Script.sol";
import {AttestationTracker, IEAS} from "../src/AttestationTracker.sol";
import {QuorumStakingTokenActivityChecker, IMultisig} from "../src/QuorumStakingTokenActivityChecker.sol";

/**
 * @title MockEAS
 * @dev Mock EAS contract for local testing.
 */
contract MockEAS {
    uint256 private _attestationCounter;
    mapping(bytes32 => bool) public attestations;

    function attestByDelegation(IEAS.DelegatedAttestationRequest calldata request)
        external
        payable
        returns (bytes32)
    {
        _attestationCounter++;
        bytes32 uid = keccak256(abi.encodePacked(_attestationCounter, block.timestamp, msg.sender));
        attestations[uid] = true;
        return uid;
    }
}

/**
 * @title MockMultisig
 * @dev Mock multisig contract for local testing.
 */
contract MockMultisig is IMultisig {
    uint256 private _nonce;

    function nonce() external view override returns (uint256) {
        return _nonce;
    }

    function incrementNonce() external {
        _nonce++;
    }

    function executeTransaction() external {
        // Simulate executing a transaction
        _nonce++;
        console.log("Transaction executed, nonce is now:", _nonce);
    }
}

/**
 * @title TestQuorumStakingIntegrationScript
 * @dev Script to test QuorumStaking integration on local testnet with deployed contracts.
 *
 * This script demonstrates:
 * 1. Deploying all required contracts
 * 2. Making attestations through AttestationTracker
 * 3. Verifying QuorumStakingTokenActivityChecker sees the updates
 * 4. Testing liveness ratio calculations
 *
 * Usage:
 *   # Run on local anvil testnet
 *   forge script script/TestQuorumStakingIntegration.s.sol --fork-url http://localhost:8545 --broadcast
 */
contract TestQuorumStakingIntegrationScript is Script {
    // Default configuration
    uint256 public constant DEFAULT_LIVENESS_RATIO = 1e15; // 1e15 per second

    function run() public {
        uint256 deployerPrivateKey = vm.envUint("PRIVATE_KEY");
        address deployer = vm.addr(deployerPrivateKey);

        console.log("=== QuorumStaking Integration Test ===");
        console.log("Deployer:", deployer);
        console.log("Liveness Ratio:", DEFAULT_LIVENESS_RATIO);

        vm.startBroadcast(deployerPrivateKey);

        // Step 1: Deploy all contracts
        console.log("\n1. Deploying contracts...");

        MockEAS mockEAS = new MockEAS();
        console.log("MockEAS deployed to:", address(mockEAS));

        AttestationTracker attestationTracker = new AttestationTracker(deployer, address(mockEAS));
        console.log("AttestationTracker deployed to:", address(attestationTracker));

        QuorumStakingTokenActivityChecker stakingChecker = new QuorumStakingTokenActivityChecker(
            address(attestationTracker),
            DEFAULT_LIVENESS_RATIO
        );
        console.log("QuorumStakingTokenActivityChecker deployed to:", address(stakingChecker));

        MockMultisig mockMultisig = new MockMultisig();
        console.log("MockMultisig deployed to:", address(mockMultisig));

        // Step 2: Verify initial state
        console.log("\n2. Verifying initial state...");

        uint256[] memory initialNonces = stakingChecker.getMultisigNonces(address(mockMultisig));
        console.log("Initial multisig nonce:", initialNonces[0]);
        console.log("Initial casted votes:", initialNonces[1]);
        console.log("Initial voting opportunities:", initialNonces[2]);
        console.log("Initial no voting opportunities:", initialNonces[3]);

        // Step 3: Make some attestations
        console.log("\n3. Making attestations...");

        // Make first attestation
        _makeAttestation(attestationTracker, address(mockMultisig));
        console.log("Made first attestation");

        uint256[] memory afterFirstNonces = stakingChecker.getMultisigNonces(address(mockMultisig));
        console.log("After first attestation - casted votes:", afterFirstNonces[1]);

        // Make second attestation
        _makeAttestation(attestationTracker, address(mockMultisig));
        console.log("Made second attestation");

        uint256[] memory afterSecondNonces = stakingChecker.getMultisigNonces(address(mockMultisig));
        console.log("After second attestation - casted votes:", afterSecondNonces[1]);

        // Step 4: Simulate multisig transactions
        console.log("\n4. Simulating multisig transactions...");

        mockMultisig.executeTransaction();
        mockMultisig.executeTransaction();

        uint256[] memory afterTransactionsNonces = stakingChecker.getMultisigNonces(address(mockMultisig));
        console.log("After transactions - multisig nonce:", afterTransactionsNonces[0]);

        // Step 5: Test ratio calculations
        console.log("\n5. Testing ratio calculations...");

        // Simulate time-based scenario
        uint256[] memory oldNonces = _createNonces(0, 0, 0, 0);  // Starting state
        uint256[] memory newNonces = afterTransactionsNonces;    // Current state
        uint256 timespan = 3600; // 1 hour

        bool ratioResult = stakingChecker.isRatioPass(newNonces, oldNonces, timespan);
        console.log("Ratio test result:", ratioResult);
        console.log("Time span used:", timespan, "seconds");

        // Calculate and display the actual ratio
        if (newNonces[1] > oldNonces[1] && timespan > 0) {
            uint256 attestationDiff = newNonces[1] - oldNonces[1];
            uint256 ratio = (attestationDiff * 1e18) / timespan;
            console.log("Calculated ratio:", ratio);
            console.log("Required ratio:", DEFAULT_LIVENESS_RATIO);
            console.log("Ratio check:", ratio >= DEFAULT_LIVENESS_RATIO ? "PASS" : "FAIL");
        }

        // Step 6: Test edge cases
        console.log("\n6. Testing edge cases...");

        // Test with no nonce change
        bool noNonceChangeResult = stakingChecker.isRatioPass(newNonces, newNonces, timespan);
        console.log("No nonce change result:", noNonceChangeResult);

        // Test with zero timespan
        bool zeroTimespanResult = stakingChecker.isRatioPass(newNonces, oldNonces, 0);
        console.log("Zero timespan result:", zeroTimespanResult);

        vm.stopBroadcast();

        // Step 7: Display final summary
        console.log("\n=== Integration Test Summary ===");
        console.log("All contracts deployed successfully");
        console.log("AttestationTracker address:", address(attestationTracker));
        console.log("QuorumStakingTokenActivityChecker address:", address(stakingChecker));
        console.log("MockMultisig address:", address(mockMultisig));
        console.log("Total attestations made:", afterSecondNonces[1]);
        console.log("Final multisig nonce:", afterTransactionsNonces[0]);
        console.log("Integration test completed successfully!");

        // Step 8: Provide next steps
        console.log("\n=== Next Steps ===");
        console.log("To interact with deployed contracts:");
        console.log("1. AttestationTracker:", address(attestationTracker));
        console.log("2. QuorumStakingTokenActivityChecker:", address(stakingChecker));
        console.log("3. Use getMultisigNonces() to query current state");
        console.log("4. Use isRatioPass() to test liveness calculations");
    }

    /**
     * @dev Helper function to make an attestation.
     */
    function _makeAttestation(AttestationTracker tracker, address multisig) internal returns (bytes32) {
        IEAS.DelegatedAttestationRequest memory request = IEAS.DelegatedAttestationRequest({
            schema: bytes32(uint256(1)),
            data: abi.encode("test integration data"),
            expirationTime: uint64(block.timestamp + 3600),
            revocable: false,
            refUID: bytes32(0),
            recipient: multisig,
            value: 0,
            deadline: uint64(block.timestamp + 1800),
            signature: hex"0123456789abcdef"
        });

        return tracker.attestByDelegation(request);
    }

    /**
     * @dev Helper to create nonce arrays.
     */
    function _createNonces(uint256 multisigNonce, uint256 casted, uint256 opportunities, uint256 noOpportunities)
        internal
        pure
        returns (uint256[] memory nonces)
    {
        nonces = new uint256[](4);
        nonces[0] = multisigNonce;
        nonces[1] = casted;
        nonces[2] = opportunities;
        nonces[3] = noOpportunities;
    }
}
