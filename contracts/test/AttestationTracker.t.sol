// SPDX-License-Identifier: MIT
pragma solidity 0.8.24;

import {Test, console} from "forge-std/Test.sol";
import {AttestationTracker, IEAS} from "../src/AttestationTracker.sol";

/**
 * @title MockEAS
 * @dev Mock EAS contract for testing purposes with correct interface.
 */
contract MockEAS {
    uint256 private _attestationCounter;

    mapping(bytes32 => bool) public attestations;

    function attestByDelegation(
        IEAS.DelegatedAttestationRequest calldata,
        IEAS.Signature calldata,
        address,
        uint64
    ) external payable returns (bytes32) {
        _attestationCounter++;
        bytes32 uid = keccak256(abi.encodePacked(_attestationCounter, block.timestamp));
        attestations[uid] = true;
        return uid;
    }
}

/**
 * @title AttestationTrackerTest
 * @dev Comprehensive test suite for the AttestationTracker contract.
 *
 * Tests focus on:
 * - Core attestation wrapper functionality
 * - Simple attestation counting
 * - Gas efficiency and edge cases
 * - Multi-multisig independent tracking
 */
contract AttestationTrackerTest is Test {
    AttestationTracker public tracker;
    MockEAS public mockEAS;

    // Test addresses
    address public owner = makeAddr("owner");
    address public multisig1 = makeAddr("multisig1");
    address public multisig2 = makeAddr("multisig2");
    address public unauthorized = makeAddr("unauthorized");

    // Events for testing
    event AttestationMade(address indexed multisig, bytes32 indexed attestationUID);

    /**
     * @dev Sets up the test environment before each test.
     * Deploys mock EAS and AttestationTracker contracts with proper configuration.
     */
    function setUp() public {
        // Deploy mock EAS
        mockEAS = new MockEAS();

        // Deploy the attestation tracker
        tracker = new AttestationTracker(owner, address(mockEAS));

        // Verify initial setup
        assertEq(tracker.owner(), owner, "Owner should be set correctly");
        assertEq(tracker.EAS(), address(mockEAS), "EAS address should be set correctly");
    }

    // --- Constructor Tests ---

    /**
     * @dev Test that constructor rejects zero EAS address.
     * This ensures the contract cannot be deployed with an invalid EAS address.
     */
    function test_RevertWhen_Constructor_ZeroEAS() public {
        vm.expectRevert("AttestationTracker: EAS address cannot be zero");
        new AttestationTracker(owner, address(0));
    }

    /**
     * @dev Test successful constructor with valid parameters.
     * Verifies that initial state is properly set up.
     */
    function test_Constructor_Success() public view {
        assertEq(tracker.owner(), owner, "Owner should be set correctly");
        assertEq(tracker.EAS(), address(mockEAS), "EAS address should be set correctly");

        // Initial attestation count should be zero
        assertEq(tracker.getNumAttestations(multisig1), 0, "Initial attestation count should be 0");
    }

    // --- Helper Functions ---

    /**
     * @dev Create a test attestation request with the correct nested structure.
     */
    function _createTestRequest() internal view returns (IEAS.DelegatedAttestationRequest memory) {
        IEAS.AttestationRequestData memory data = IEAS.AttestationRequestData({
            recipient: multisig1,
            expirationTime: uint64(block.timestamp + 3600),
            revocable: false,
            refUID: bytes32(0),
            data: abi.encode("test data"),
            value: 0
        });

        return IEAS.DelegatedAttestationRequest({
            schema: bytes32(uint256(1)),
            data: data
        });
    }

    /**
     * @dev Create a test signature.
     */
    function _createTestSignature() internal pure returns (IEAS.Signature memory) {
        return IEAS.Signature({
            v: 27,
            r: bytes32(uint256(1)),
            s: bytes32(uint256(2))
        });
    }

    // --- Attestation Wrapper Tests ---

    /**
     * @dev Test successful attestation through wrapper.
     * This tests the core attestation wrapper functionality that forwards to EAS
     * while incrementing the local attestation counter.
     */
    function test_AttestByDelegation_Success() public {
        IEAS.DelegatedAttestationRequest memory request = _createTestRequest();
        IEAS.Signature memory signature = _createTestSignature();
        uint64 deadline = uint64(block.timestamp + 1800);

        vm.prank(multisig1);
        bytes32 attestationUID = tracker.attestByDelegation(request, signature, multisig1, deadline);

        // Verify attestation was created
        assertTrue(attestationUID != bytes32(0), "Attestation UID should not be zero");
        assertTrue(mockEAS.attestations(attestationUID), "Attestation should exist in mock EAS");

        // Verify attestation counter increased
        assertEq(tracker.getNumAttestations(multisig1), 1, "Attestation count should be 1");
    }

    /**
     * @dev Test attestation wrapper emits event.
     * This ensures proper event emission for off-chain tracking.
     */
    function test_AttestByDelegation_EmitsEvent() public {
        IEAS.DelegatedAttestationRequest memory request = _createTestRequest();
        IEAS.Signature memory signature = _createTestSignature();
        uint64 deadline = uint64(block.timestamp + 1800);

        vm.expectEmit(true, false, false, false);
        emit AttestationMade(multisig1, bytes32(0)); // Only check multisig address, ignore UID

        vm.prank(multisig1);
        tracker.attestByDelegation(request, signature, multisig1, deadline);
    }

    /**
     * @dev Test multiple attestations increment counter correctly.
     * This verifies that the attestation counter properly increments with each attestation.
     */
    function test_AttestByDelegation_MultipleAttestations() public {
        IEAS.DelegatedAttestationRequest memory request = _createTestRequest();
        IEAS.Signature memory signature = _createTestSignature();
        uint64 deadline = uint64(block.timestamp + 1800);

        vm.startPrank(multisig1);

        // Make multiple attestations
        tracker.attestByDelegation(request, signature, multisig1, deadline);
        tracker.attestByDelegation(request, signature, multisig1, deadline);
        tracker.attestByDelegation(request, signature, multisig1, deadline);

        vm.stopPrank();

        assertEq(tracker.getNumAttestations(multisig1), 3, "Should have 3 attestations");
    }

    /**
     * @dev Test attestation with ETH value forwarding.
     * This ensures that ETH sent with attestations is properly forwarded to EAS.
     */
    function test_AttestByDelegation_WithValue() public {
        // Create request with value
        IEAS.AttestationRequestData memory data = IEAS.AttestationRequestData({
            recipient: multisig1,
            expirationTime: uint64(block.timestamp + 3600),
            revocable: false,
            refUID: bytes32(0),
            data: abi.encode("test data"),
            value: 1 ether
        });

        IEAS.DelegatedAttestationRequest memory request = IEAS.DelegatedAttestationRequest({
            schema: bytes32(uint256(1)),
            data: data
        });

        IEAS.Signature memory signature = _createTestSignature();
        uint64 deadline = uint64(block.timestamp + 1800);

        // Give multisig1 some ETH
        vm.deal(multisig1, 2 ether);

        uint256 initialBalance = address(mockEAS).balance;

        vm.prank(multisig1);
        tracker.attestByDelegation{value: 1 ether}(request, signature, multisig1, deadline);

        // Verify ETH was forwarded to EAS
        assertEq(address(mockEAS).balance, initialBalance + 1 ether, "ETH should be forwarded to EAS");
        assertEq(tracker.getNumAttestations(multisig1), 1, "Attestation count should still increment");
    }

    // --- Multi-Multisig Independent Tracking Tests ---

    /**
     * @dev Test that different multisigs have independent attestation tracking.
     * This ensures that each multisig's attestations and status are tracked separately.
     */
    function test_IndependentMultisigs_AttestationTracking() public {
        IEAS.DelegatedAttestationRequest memory request = _createTestRequest();
        IEAS.Signature memory signature = _createTestSignature();
        uint64 deadline = uint64(block.timestamp + 1800);

        // multisig1 makes 2 attestations
        vm.startPrank(multisig1);
        tracker.attestByDelegation(request, signature, multisig1, deadline);
        tracker.attestByDelegation(request, signature, multisig1, deadline);
        vm.stopPrank();

        // multisig2 makes 1 attestation
        vm.prank(multisig2);
        tracker.attestByDelegation(request, signature, multisig2, deadline);

        // Verify independent tracking
        assertEq(tracker.getNumAttestations(multisig1), 2, "Multisig1 should have 2 attestations");
        assertEq(tracker.getNumAttestations(multisig2), 1, "Multisig2 should have 1 attestation");
    }

    // --- IQuorumTracker Interface Tests ---

    /**
     * @dev Test IQuorumTracker getVotingStats implementation.
     * This tests the new IQuorumTracker interface functionality.
     */
    function test_GetVotingStats_ReturnsCorrectFormat() public {
        IEAS.DelegatedAttestationRequest memory request = _createTestRequest();
        IEAS.Signature memory signature = _createTestSignature();
        uint64 deadline = uint64(block.timestamp + 1800);

        // Make 3 attestations for multisig1
        vm.startPrank(multisig1);
        tracker.attestByDelegation(request, signature, multisig1, deadline);
        tracker.attestByDelegation(request, signature, multisig1, deadline);
        tracker.attestByDelegation(request, signature, multisig1, deadline);
        vm.stopPrank();

        // Get voting stats
        uint256[] memory stats = tracker.getVotingStats(multisig1);

        // Check array length
        assertEq(stats.length, 3, "Should return 3 elements");

        // Check values (all should equal attestation count for now)
        assertEq(stats[0], 3, "Casted votes should equal attestation count");
        assertEq(stats[1], 3, "Voting opportunities should equal attestation count");
        assertEq(stats[2], 0, "No voting opportunities should be 0");
    }

    /**
     * @dev Test getVotingStats for address with no attestations.
     */
    function test_GetVotingStats_EmptyAddress() public {
        address randomAddr = makeAddr("random");
        uint256[] memory stats = tracker.getVotingStats(randomAddr);

        assertEq(stats.length, 3, "Should return 3 elements");
        assertEq(stats[0], 0, "Casted votes should be 0");
        assertEq(stats[1], 0, "Voting opportunities should be 0");
        assertEq(stats[2], 0, "No voting opportunities should be 0");
    }

    // --- Edge Case Tests ---

    /**
     * @dev Test attestation counter overflow protection.
     * Since Solidity 0.8.x has built-in overflow protection, this test
     * verifies the counter can safely reach high values.
     */
    function test_EdgeCase_CounterOverflow() public {
        // Set counter to max uint256 - 1
        vm.store(
            address(tracker),
            keccak256(abi.encode(multisig1, uint256(1))), // slot for mapMultisigAttestations[multisig1]
            bytes32(type(uint256).max - 1)
        );

        assertEq(tracker.getNumAttestations(multisig1), type(uint256).max - 1, "Counter should be at max - 1");

        IEAS.DelegatedAttestationRequest memory request = _createTestRequest();
        IEAS.Signature memory signature = _createTestSignature();
        uint64 deadline = uint64(block.timestamp + 1800);

        // This should increment to max uint256
        vm.prank(multisig1);
        tracker.attestByDelegation(request, signature, multisig1, deadline);

        assertEq(tracker.getNumAttestations(multisig1), type(uint256).max, "Counter should be at max");
    }

    /**
     * @dev Test getNumAttestations for various addresses.
     * This verifies that uninitialized addresses return 0.
     */
    function test_GetNumAttestations_UninitializedAddresses() public view {
        assertEq(tracker.getNumAttestations(address(0)), 0, "Zero address should have 0 attestations");
        assertEq(tracker.getNumAttestations(unauthorized), 0, "Uninitialized address should have 0 attestations");
        assertEq(tracker.getNumAttestations(owner), 0, "Owner should have 0 attestations initially");
    }

    // --- Gas Optimization Tests ---

    /**
     * @dev Test gas consumption for attestation operations.
     * This helps track and optimize gas usage over time.
     */
    function test_Gas_AttestByDelegation() public {
        IEAS.DelegatedAttestationRequest memory request = _createTestRequest();
        IEAS.Signature memory signature = _createTestSignature();
        uint64 deadline = uint64(block.timestamp + 1800);

        vm.prank(multisig1);
        uint256 gasBefore = gasleft();
        tracker.attestByDelegation(request, signature, multisig1, deadline);
        uint256 gasUsed = gasBefore - gasleft();

        console.log("Gas used for attestByDelegation:", gasUsed);
        // Typical gas usage should be around 50k-100k
        assertLt(gasUsed, 150000, "Gas usage should be reasonable");
    }

    /**
     * @dev Test gas consumption for view functions.
     */
    function test_Gas_ViewFunctions() public {
        // Setup: Make some attestations
        IEAS.DelegatedAttestationRequest memory request = _createTestRequest();
        IEAS.Signature memory signature = _createTestSignature();
        uint64 deadline = uint64(block.timestamp + 1800);

        vm.prank(multisig1);
        tracker.attestByDelegation(request, signature, multisig1, deadline);

        // Test getNumAttestations gas
        uint256 gasBefore = gasleft();
        tracker.getNumAttestations(multisig1);
        uint256 gasUsed = gasBefore - gasleft();
        console.log("Gas used for getNumAttestations:", gasUsed);
        assertLt(gasUsed, 10000, "View function should be cheap");

        // Test getVotingStats gas
        gasBefore = gasleft();
        tracker.getVotingStats(multisig1);
        gasUsed = gasBefore - gasleft();
        console.log("Gas used for getVotingStats:", gasUsed);
        assertLt(gasUsed, 20000, "View function should be cheap");
    }

    // --- Fuzz Tests ---

    /**
     * @dev Fuzz test for attestation counting.
     * This ensures the counter works correctly with random inputs.
     */
    function testFuzz_AttestationCounting(address multisig, uint8 numAttestations) public {
        vm.assume(multisig != address(0));
        vm.assume(numAttestations > 0 && numAttestations <= 100); // Reasonable range

        IEAS.DelegatedAttestationRequest memory request = _createTestRequest();
        IEAS.Signature memory signature = _createTestSignature();
        uint64 deadline = uint64(block.timestamp + 1800);

        vm.startPrank(multisig);
        for (uint8 i = 0; i < numAttestations; i++) {
            tracker.attestByDelegation(request, signature, multisig, deadline);
        }
        vm.stopPrank();

        assertEq(tracker.getNumAttestations(multisig), numAttestations, "Count should match attestations made");
    }

    /**
     * @dev Fuzz test for multiple multisigs.
     * This ensures independent tracking works with random addresses.
     */
    function testFuzz_IndependentMultisigs(
        address multisigA,
        address multisigB,
        uint8 countA,
        uint8 countB
    ) public {
        vm.assume(multisigA != address(0) && multisigB != address(0));
        vm.assume(multisigA != multisigB);
        vm.assume(countA <= 50 && countB <= 50); // Reasonable range

        IEAS.DelegatedAttestationRequest memory request = _createTestRequest();
        IEAS.Signature memory signature = _createTestSignature();
        uint64 deadline = uint64(block.timestamp + 1800);

        // MultisigA attestations
        vm.startPrank(multisigA);
        for (uint8 i = 0; i < countA; i++) {
            tracker.attestByDelegation(request, signature, multisigA, deadline);
        }
        vm.stopPrank();

        // MultisigB attestations
        vm.startPrank(multisigB);
        for (uint8 i = 0; i < countB; i++) {
            tracker.attestByDelegation(request, signature, multisigB, deadline);
        }
        vm.stopPrank();

        assertEq(tracker.getNumAttestations(multisigA), countA, "MultisigA count should be correct");
        assertEq(tracker.getNumAttestations(multisigB), countB, "MultisigB count should be correct");
    }
}