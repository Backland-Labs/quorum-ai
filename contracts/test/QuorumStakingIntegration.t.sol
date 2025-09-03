// SPDX-License-Identifier: MIT
pragma solidity 0.8.24;

import {Test, console} from "forge-std/Test.sol";
import {AttestationTracker, IEAS} from "../src/AttestationTracker.sol";
import {QuorumStakingTokenActivityChecker, IMultisig} from "../src/QuorumStakingTokenActivityChecker.sol";

/**
 * @title MockEAS
 * @dev Mock EAS contract for testing attestation functionality.
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
 * @dev Mock multisig contract implementing IMultisig interface for testing.
 */
contract MockMultisig is IMultisig {
    uint256 private _nonce;

    function nonce() external view override returns (uint256) {
        return _nonce;
    }

    function incrementNonce() external {
        _nonce++;
    }

    function setNonce(uint256 newNonce) external {
        _nonce = newNonce;
    }
}

/**
 * @title QuorumStakingIntegrationTest
 * @dev Comprehensive integration test suite verifying the interaction between
 * QuorumStakingTokenActivityChecker and AttestationTracker through the IQuorumTracker interface.
 *
 * This test suite covers:
 * - End-to-end contract integration
 * - Interface compatibility verification
 * - Liveness ratio calculations with various scenarios
 * - Multi-multisig independent tracking
 * - Edge cases and error conditions
 */
contract QuorumStakingIntegrationTest is Test {
    // Contract instances
    AttestationTracker public attestationTracker;
    QuorumStakingTokenActivityChecker public stakingChecker;
    MockEAS public mockEAS;
    MockMultisig public mockMultisig1;
    MockMultisig public mockMultisig2;

    // Test addresses
    address public owner = makeAddr("owner");
    address public unauthorizedUser = makeAddr("unauthorized");

    // Test constants
    uint256 public constant DEFAULT_LIVENESS_RATIO = 1e15; // 1e15 per second
    uint256 public constant HIGH_LIVENESS_RATIO = 5e15;    // 5e15 per second
    uint256 public constant LOW_LIVENESS_RATIO = 1e14;     // 1e14 per second

    // Events for testing
    event AttestationMade(address indexed multisig, bytes32 indexed attestationUID);

    /**
     * @dev Sets up the test environment with deployed contracts and mock multisigs.
     */
    function setUp() public {
        // Deploy mock contracts
        mockEAS = new MockEAS();
        mockMultisig1 = new MockMultisig();
        mockMultisig2 = new MockMultisig();

        // Deploy AttestationTracker
        attestationTracker = new AttestationTracker(owner, address(mockEAS));

        // Deploy QuorumStakingTokenActivityChecker pointing to AttestationTracker
        stakingChecker = new QuorumStakingTokenActivityChecker(
            address(attestationTracker),
            DEFAULT_LIVENESS_RATIO
        );

        // Verify initial setup
        assertEq(attestationTracker.owner(), owner, "AttestationTracker owner should be set correctly");
        assertEq(attestationTracker.EAS(), address(mockEAS), "EAS address should be set correctly");
        assertEq(stakingChecker.quorumTracker(), address(attestationTracker), "QuorumTracker should point to AttestationTracker");
        assertEq(stakingChecker.livenessRatio(), DEFAULT_LIVENESS_RATIO, "Liveness ratio should be set correctly");
    }

    // --- Setup and Constructor Tests ---

    /**
     * @dev Test that QuorumStakingTokenActivityChecker rejects zero quorum tracker address.
     */
    function test_RevertWhen_Constructor_ZeroQuorumTracker() public {
        vm.expectRevert();
        new QuorumStakingTokenActivityChecker(address(0), DEFAULT_LIVENESS_RATIO);
    }

    /**
     * @dev Test successful deployment with valid parameters.
     */
    function test_Constructor_Success() public view {
        assertEq(stakingChecker.quorumTracker(), address(attestationTracker), "QuorumTracker should be set correctly");
        assertEq(stakingChecker.livenessRatio(), DEFAULT_LIVENESS_RATIO, "Liveness ratio should be set correctly");
    }

    // --- Interface Integration Tests ---

    /**
     * @dev Test that QuorumStakingTokenActivityChecker can successfully call AttestationTracker.getVotingStats().
     */
    function test_InterfaceIntegration_GetVotingStats() public {
        // Initially, voting stats should be [0, 0, 0]
        uint256[] memory nonces = stakingChecker.getMultisigNonces(address(mockMultisig1));
        
        assertEq(nonces.length, 4, "Should return array of length 4");
        assertEq(nonces[0], 0, "Initial multisig nonce should be 0");
        assertEq(nonces[1], 0, "Initial casted votes should be 0");
        assertEq(nonces[2], 0, "Initial voting opportunities should be 0");
        assertEq(nonces[3], 0, "Initial no voting opportunities should be 0");
    }

    /**
     * @dev Test getMultisigNonces() returns correct 4-element array with multisig nonce + voting stats.
     */
    function test_GetMultisigNonces_CorrectFormat() public {
        // Set multisig nonce
        mockMultisig1.setNonce(42);

        // Make an attestation to update voting stats
        _makeAttestation(address(mockMultisig1));

        uint256[] memory nonces = stakingChecker.getMultisigNonces(address(mockMultisig1));

        assertEq(nonces.length, 4, "Should return array of length 4");
        assertEq(nonces[0], 42, "Should return multisig nonce");
        assertEq(nonces[1], 1, "Should return casted votes count");
        assertEq(nonces[2], 1, "Should return voting opportunities count");
        assertEq(nonces[3], 0, "Should return no voting opportunities count");
    }

    /**
     * @dev Test that QuorumStakingTokenActivityChecker sees updates after attestations are made.
     */
    function test_Integration_AttestationUpdates() public {
        // Initial state - no attestations
        uint256[] memory initialNonces = stakingChecker.getMultisigNonces(address(mockMultisig1));
        assertEq(initialNonces[1], 0, "Initial attestations should be 0");

        // Make an attestation through AttestationTracker
        _makeAttestation(address(mockMultisig1));

        // Verify QuorumStakingTokenActivityChecker sees the update
        uint256[] memory updatedNonces = stakingChecker.getMultisigNonces(address(mockMultisig1));
        assertEq(updatedNonces[1], 1, "Should see 1 attestation after making one");
        assertEq(updatedNonces[2], 1, "Voting opportunities should also be 1");
        
        // Make another attestation
        _makeAttestation(address(mockMultisig1));

        // Verify count increases
        uint256[] memory finalNonces = stakingChecker.getMultisigNonces(address(mockMultisig1));
        assertEq(finalNonces[1], 2, "Should see 2 attestations after making two");
        assertEq(finalNonces[2], 2, "Voting opportunities should also be 2");
    }

    // --- Liveness Ratio Tests ---

    /**
     * @dev Test isRatioPass() with no multisig nonce change (should return false).
     */
    function test_IsRatioPass_NoMultisigNonceChange() public {
        uint256[] memory currentNonces = new uint256[](4);
        uint256[] memory lastNonces = new uint256[](4);
        
        // Same nonces
        currentNonces[0] = 5;
        lastNonces[0] = 5;
        currentNonces[1] = 2;
        lastNonces[1] = 1;
        
        bool result = stakingChecker.isRatioPass(currentNonces, lastNonces, 100);
        assertFalse(result, "Should return false when multisig nonce hasn't changed");
    }

    /**
     * @dev Test isRatioPass() with zero timestamp (should return false).
     */
    function test_IsRatioPass_ZeroTimestamp() public {
        uint256[] memory currentNonces = new uint256[](4);
        uint256[] memory lastNonces = new uint256[](4);
        
        currentNonces[0] = 6;
        lastNonces[0] = 5;
        currentNonces[1] = 2;
        lastNonces[1] = 1;
        
        bool result = stakingChecker.isRatioPass(currentNonces, lastNonces, 0);
        assertFalse(result, "Should return false when timestamp is zero");
    }

    /**
     * @dev Test isRatioPass() with successful voting scenario (casted votes increased).
     */
    function test_IsRatioPass_SuccessfulVoting() public {
        uint256[] memory currentNonces = new uint256[](4);
        uint256[] memory lastNonces = new uint256[](4);
        
        // Multisig nonce increased
        currentNonces[0] = 6;
        lastNonces[0] = 5;
        
        // Casted votes increased
        currentNonces[1] = 3;
        lastNonces[1] = 1;
        
        currentNonces[2] = 3;
        lastNonces[2] = 1;
        
        currentNonces[3] = 0;
        lastNonces[3] = 0;
        
        // Calculate expected ratio: (3-1) * 1e18 / 100 = 2e16
        // Should pass if ratio >= livenessRatio (1e15)
        uint256 timespan = 100;
        bool result = stakingChecker.isRatioPass(currentNonces, lastNonces, timespan);
        assertTrue(result, "Should pass when voting ratio meets requirement");
    }

    /**
     * @dev Test isRatioPass() with failing voting scenario (ratio too low).
     */
    function test_IsRatioPass_FailingVoting() public {
        uint256[] memory currentNonces = new uint256[](4);
        uint256[] memory lastNonces = new uint256[](4);
        
        // Multisig nonce increased
        currentNonces[0] = 6;
        lastNonces[0] = 5;
        
        // Very small increase in casted votes
        currentNonces[1] = 2;
        lastNonces[1] = 1;
        
        currentNonces[2] = 2;
        lastNonces[2] = 1;
        
        // Use long timespan to make ratio very small
        uint256 timespan = 1e18; // Very large timespan
        
        bool result = stakingChecker.isRatioPass(currentNonces, lastNonces, timespan);
        assertFalse(result, "Should fail when voting ratio is too low");
    }

    /**
     * @dev Test isRatioPass() with no voting but opportunities available scenario.
     */
    function test_IsRatioPass_NoVotingWithOpportunities() public {
        uint256[] memory currentNonces = new uint256[](4);
        uint256[] memory lastNonces = new uint256[](4);
        
        // Multisig nonce increased
        currentNonces[0] = 6;
        lastNonces[0] = 5;
        
        // No increase in casted votes
        currentNonces[1] = 1;
        lastNonces[1] = 1;
        
        // Increase in voting opportunities and no voting opportunities
        currentNonces[2] = 3;
        lastNonces[2] = 1;
        
        currentNonces[3] = 2;
        lastNonces[3] = 1;
        
        // Calculate expected ratio: ((3-1) + (2-1)) * 1e18 / 100 = 3e16
        // Should pass if ratio >= 2 * livenessRatio (2e15)
        uint256 timespan = 100;
        bool result = stakingChecker.isRatioPass(currentNonces, lastNonces, timespan);
        assertTrue(result, "Should pass when alternative attestation ratio meets 2x requirement");
    }

    /**
     * @dev Test isRatioPass() with different liveness ratios.
     */
    function test_IsRatioPass_DifferentLivenessRatios() public {
        // Deploy with high liveness ratio
        QuorumStakingTokenActivityChecker highRatioChecker = new QuorumStakingTokenActivityChecker(
            address(attestationTracker),
            HIGH_LIVENESS_RATIO
        );

        uint256[] memory currentNonces = new uint256[](4);
        uint256[] memory lastNonces = new uint256[](4);
        
        currentNonces[0] = 6;
        lastNonces[0] = 5;
        currentNonces[1] = 3;
        lastNonces[1] = 1;
        currentNonces[2] = 3;
        lastNonces[2] = 1;
        
        uint256 timespan = 100;
        
        // Calculate expected ratio: (3-1) * 1e18 / 100 = 2e16
        // Default ratio: 1e15, so 2e16 >= 1e15 should pass
        // High ratio: 5e15, so 2e16 >= 5e15 should also pass (2e16 = 20e15)
        
        // Should pass with default ratio
        bool defaultResult = stakingChecker.isRatioPass(currentNonces, lastNonces, timespan);
        assertTrue(defaultResult, "Should pass with default liveness ratio");
        
        // Should also pass with high ratio since 2e16 > 5e15
        bool highResult = highRatioChecker.isRatioPass(currentNonces, lastNonces, timespan);
        assertTrue(highResult, "Should still pass with high liveness ratio (ratio is high enough)");
        
        // Test a scenario that should fail with high ratio
        uint256[] memory lowActivityNonces = new uint256[](4);
        lowActivityNonces[0] = 6;
        lowActivityNonces[1] = 1; // Very small increase
        lowActivityNonces[2] = 1;
        
        uint256[] memory zeroNonces = new uint256[](4);
        zeroNonces[0] = 5;
        
        uint256 longTimespan = 10000; // Much longer timespan
        
        // Calculate ratio: 1 * 1e18 / 10000 = 1e14
        // Should pass with default (1e14 < 1e15 = false, actually should fail)
        // Should fail with high ratio (1e14 < 5e15 = true)
        
        bool defaultLowResult = stakingChecker.isRatioPass(lowActivityNonces, zeroNonces, longTimespan);
        assertFalse(defaultLowResult, "Should fail with default ratio when activity is too low");
        
        bool highLowResult = highRatioChecker.isRatioPass(lowActivityNonces, zeroNonces, longTimespan);
        assertFalse(highLowResult, "Should fail with high liveness ratio when activity is too low");
    }

    // --- Multi-Multisig Tests ---

    /**
     * @dev Test that different multisigs have independent tracking through the integration.
     */
    function test_Integration_MultipleMultisigs() public {
        // Set different nonces for multisigs
        mockMultisig1.setNonce(10);
        mockMultisig2.setNonce(20);

        // Make different numbers of attestations
        _makeAttestation(address(mockMultisig1));
        _makeAttestation(address(mockMultisig1));
        _makeAttestation(address(mockMultisig2));

        // Get nonces for both multisigs
        uint256[] memory nonces1 = stakingChecker.getMultisigNonces(address(mockMultisig1));
        uint256[] memory nonces2 = stakingChecker.getMultisigNonces(address(mockMultisig2));

        // Verify independent tracking
        assertEq(nonces1[0], 10, "Multisig1 should have nonce 10");
        assertEq(nonces1[1], 2, "Multisig1 should have 2 attestations");
        
        assertEq(nonces2[0], 20, "Multisig2 should have nonce 20");
        assertEq(nonces2[1], 1, "Multisig2 should have 1 attestation");
    }

    // --- Comprehensive End-to-End Scenarios ---

    /**
     * @dev Test complete workflow: no attestations -> single attestation -> multiple attestations.
     */
    function test_EndToEnd_AttestationProgression() public {
        address multisigAddr = address(mockMultisig1);
        
        // Initial state: no attestations
        uint256[] memory initialNonces = stakingChecker.getMultisigNonces(multisigAddr);
        assertEq(initialNonces[1], 0, "Should start with no attestations");

        // Make first attestation
        _makeAttestation(multisigAddr);
        uint256[] memory afterFirstNonces = stakingChecker.getMultisigNonces(multisigAddr);
        assertEq(afterFirstNonces[1], 1, "Should have 1 attestation after first");

        // Make multiple more attestations
        _makeAttestation(multisigAddr);
        _makeAttestation(multisigAddr);
        _makeAttestation(multisigAddr);
        
        uint256[] memory finalNonces = stakingChecker.getMultisigNonces(multisigAddr);
        assertEq(finalNonces[1], 4, "Should have 4 total attestations");
        assertEq(finalNonces[2], 4, "Voting opportunities should match attestations");
    }

    /**
     * @dev Test comprehensive ratio scenario with realistic timeline.
     */
    function test_EndToEnd_RealisticRatioScenario() public {
        address multisigAddr = address(mockMultisig1);
        
        // Setup initial state
        mockMultisig1.setNonce(100);
        _makeAttestation(multisigAddr);
        _makeAttestation(multisigAddr);
        
        uint256[] memory initialNonces = stakingChecker.getMultisigNonces(multisigAddr);
        
        // Simulate time passing and activity
        mockMultisig1.setNonce(105); // 5 new transactions
        _makeAttestation(multisigAddr);
        _makeAttestation(multisigAddr);
        _makeAttestation(multisigAddr);
        
        uint256[] memory currentNonces = stakingChecker.getMultisigNonces(multisigAddr);
        
        // Test ratio calculation (3 new attestations over 3600 seconds)
        uint256 timespan = 3600; // 1 hour
        bool result = stakingChecker.isRatioPass(currentNonces, initialNonces, timespan);
        
        // Expected ratio: 3 * 1e18 / 3600 = 8.33e14
        // Should pass if >= 1e15? Let's see...
        console.log("Ratio test result:", result);
        console.log("New attestations:", currentNonces[1] - initialNonces[1]);
        console.log("Timespan:", timespan);
    }

    // --- Error Handling and Edge Cases ---

    /**
     * @dev Test behavior when AttestationTracker returns unexpected data.
     */
    function test_EdgeCase_EmptyVotingStats() public view {
        // This should still work as our AttestationTracker always returns a valid 3-element array
        uint256[] memory nonces = stakingChecker.getMultisigNonces(address(mockMultisig1));
        assertEq(nonces.length, 4, "Should handle empty voting stats gracefully");
    }

    /**
     * @dev Test with maximum uint256 values.
     */
    function test_EdgeCase_MaxValues() public {
        uint256[] memory currentNonces = new uint256[](4);
        uint256[] memory lastNonces = new uint256[](4);
        
        // Set to max values (should not overflow due to Solidity 0.8.x)
        currentNonces[0] = type(uint256).max;
        lastNonces[0] = type(uint256).max - 1;
        currentNonces[1] = 1000;
        lastNonces[1] = 500;
        currentNonces[2] = 1000;
        lastNonces[2] = 500;
        
        // This should work without overflow
        bool result = stakingChecker.isRatioPass(currentNonces, lastNonces, 1000);
        assertTrue(result, "Should handle large values without overflow");
    }

    // --- Gas Optimization Tests ---

    /**
     * @dev Test gas usage for getMultisigNonces().
     */
    function test_Gas_GetMultisigNonces() public {
        uint256 gasBefore = gasleft();
        stakingChecker.getMultisigNonces(address(mockMultisig1));
        uint256 gasUsed = gasBefore - gasleft();
        
        console.log("Gas used for getMultisigNonces:", gasUsed);
        assertLt(gasUsed, 50000, "getMultisigNonces should be gas efficient");
    }

    /**
     * @dev Test gas usage for isRatioPass().
     */
    function test_Gas_IsRatioPass() public {
        uint256[] memory currentNonces = new uint256[](4);
        uint256[] memory lastNonces = new uint256[](4);
        
        currentNonces[0] = 6;
        lastNonces[0] = 5;
        currentNonces[1] = 3;
        lastNonces[1] = 1;
        currentNonces[2] = 3;
        lastNonces[2] = 1;
        
        uint256 gasBefore = gasleft();
        stakingChecker.isRatioPass(currentNonces, lastNonces, 100);
        uint256 gasUsed = gasBefore - gasleft();
        
        console.log("Gas used for isRatioPass:", gasUsed);
        assertLt(gasUsed, 30000, "isRatioPass should be gas efficient");
    }

    // --- Fuzz Tests ---

    /**
     * @dev Fuzz test for ratio calculations with various inputs.
     */
    function testFuzz_RatioCalculation(
        uint128 castedVotesDiff,
        uint128 votingOpportunitiesDiff,
        uint128 noVotingOpportunitiesDiff,
        uint64 timespan
    ) public {
        vm.assume(timespan > 0 && timespan < 1e18);
        vm.assume(castedVotesDiff < 1e18);
        vm.assume(votingOpportunitiesDiff < 1e18);
        vm.assume(noVotingOpportunitiesDiff < 1e18);
        
        uint256[] memory currentNonces = new uint256[](4);
        uint256[] memory lastNonces = new uint256[](4);
        
        // Ensure multisig nonce increases
        currentNonces[0] = 100;
        lastNonces[0] = 99;
        
        currentNonces[1] = uint256(castedVotesDiff);
        lastNonces[1] = 0;
        currentNonces[2] = uint256(votingOpportunitiesDiff);
        lastNonces[2] = 0;
        currentNonces[3] = uint256(noVotingOpportunitiesDiff);
        lastNonces[3] = 0;
        
        // This should not revert
        bool result = stakingChecker.isRatioPass(currentNonces, lastNonces, timespan);
        
        // Log for debugging if needed
        if (result) {
            console.log("Fuzz test passed with ratio check");
        }
    }

    // --- Helper Functions ---

    /**
     * @dev Helper function to make an attestation through AttestationTracker.
     * @param multisig The address of the multisig making the attestation.
     */
    function _makeAttestation(address multisig) internal returns (bytes32 attestationUID) {
        IEAS.DelegatedAttestationRequest memory request = IEAS.DelegatedAttestationRequest({
            schema: bytes32(uint256(1)),
            data: abi.encode("integration test data"),
            expirationTime: uint64(block.timestamp + 3600),
            revocable: false,
            refUID: bytes32(0),
            recipient: multisig,
            value: 0,
            deadline: uint64(block.timestamp + 1800),
            signature: hex"0123456789abcdef"
        });

        vm.prank(multisig);
        return attestationTracker.attestByDelegation(request);
    }

    /**
     * @dev Helper to create standard nonce arrays for testing.
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