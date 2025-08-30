// SPDX-License-Identifier: MIT
pragma solidity 0.8.24;

import {Test, console} from "forge-std/Test.sol";
import {AttestationTracker, IEAS} from "../src/AttestationTracker.sol";

/**
 * @title MockEAS
 * @dev Mock EAS contract for testing purposes.
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



    // --- Attestation Wrapper Tests ---

    // --- Attestation Wrapper Tests ---

    /**
     * @dev Test successful attestation through wrapper.
     * This tests the core attestation wrapper functionality that forwards to EAS
     * while incrementing the local attestation counter.
     */
    function test_AttestByDelegation_Success() public {
        IEAS.DelegatedAttestationRequest memory request = IEAS.DelegatedAttestationRequest({
            schema: bytes32(uint256(1)),
            data: abi.encode("test data"),
            expirationTime: uint64(block.timestamp + 3600),
            revocable: false,
            refUID: bytes32(0),
            recipient: multisig1,
            value: 0,
            deadline: uint64(block.timestamp + 1800),
            signature: hex"0123456789abcdef"
        });

        vm.prank(multisig1);
        bytes32 attestationUID = tracker.attestByDelegation(request);

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
        IEAS.DelegatedAttestationRequest memory request = IEAS.DelegatedAttestationRequest({
            schema: bytes32(uint256(1)),
            data: abi.encode("test data"),
            expirationTime: uint64(block.timestamp + 3600),
            revocable: false,
            refUID: bytes32(0),
            recipient: multisig1,
            value: 0,
            deadline: uint64(block.timestamp + 1800),
            signature: hex"0123456789abcdef"
        });

        vm.expectEmit(true, false, false, false);
        emit AttestationMade(multisig1, bytes32(0)); // Only check multisig address, ignore UID

        vm.prank(multisig1);
        tracker.attestByDelegation(request);
    }

    /**
     * @dev Test multiple attestations increment counter correctly.
     * This verifies that the attestation counter properly increments with each attestation.
     */
    function test_AttestByDelegation_MultipleAttestations() public {
        IEAS.DelegatedAttestationRequest memory request = IEAS.DelegatedAttestationRequest({
            schema: bytes32(uint256(1)),
            data: abi.encode("test data"),
            expirationTime: uint64(block.timestamp + 3600),
            revocable: false,
            refUID: bytes32(0),
            recipient: multisig1,
            value: 0,
            deadline: uint64(block.timestamp + 1800),
            signature: hex"0123456789abcdef"
        });

        vm.startPrank(multisig1);

        // Make multiple attestations
        tracker.attestByDelegation(request);
        tracker.attestByDelegation(request);
        tracker.attestByDelegation(request);

        vm.stopPrank();

        assertEq(tracker.getNumAttestations(multisig1), 3, "Should have 3 attestations");
    }

    /**
     * @dev Test attestation with ETH value forwarding.
     * This ensures that ETH sent with attestations is properly forwarded to EAS.
     */
    function test_AttestByDelegation_WithValue() public {
        IEAS.DelegatedAttestationRequest memory request = IEAS.DelegatedAttestationRequest({
            schema: bytes32(uint256(1)),
            data: abi.encode("test data"),
            expirationTime: uint64(block.timestamp + 3600),
            revocable: false,
            refUID: bytes32(0),
            recipient: multisig1,
            value: 1 ether,
            deadline: uint64(block.timestamp + 1800),
            signature: hex"0123456789abcdef"
        });

        // Give multisig1 some ETH
        vm.deal(multisig1, 2 ether);

        uint256 initialBalance = address(mockEAS).balance;

        vm.prank(multisig1);
        tracker.attestByDelegation{value: 1 ether}(request);

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
        IEAS.DelegatedAttestationRequest memory request = IEAS.DelegatedAttestationRequest({
            schema: bytes32(uint256(1)),
            data: abi.encode("test data"),
            expirationTime: uint64(block.timestamp + 3600),
            revocable: false,
            refUID: bytes32(0),
            recipient: address(0),
            value: 0,
            deadline: uint64(block.timestamp + 1800),
            signature: hex"0123456789abcdef"
        });

        // multisig1 makes 2 attestations
        vm.startPrank(multisig1);
        tracker.attestByDelegation(request);
        tracker.attestByDelegation(request);
        vm.stopPrank();

        // multisig2 makes 1 attestation
        vm.prank(multisig2);
        tracker.attestByDelegation(request);

        // Verify independent tracking
        assertEq(tracker.getNumAttestations(multisig1), 2, "Multisig1 should have 2 attestations");
        assertEq(tracker.getNumAttestations(multisig2), 1, "Multisig2 should have 1 attestation");
    }

    // --- Fuzz Tests ---

    /**
     * @dev Fuzz test for attestation counting.
     * This tests the attestation counter with various numbers of attestations.
     */
    function testFuzz_AttestationCounting(uint8 numAttestations) public {
        vm.assume(numAttestations > 0 && numAttestations <= 100);

        IEAS.DelegatedAttestationRequest memory request = IEAS.DelegatedAttestationRequest({
            schema: bytes32(uint256(1)),
            data: abi.encode("test data"),
            expirationTime: uint64(block.timestamp + 3600),
            revocable: false,
            refUID: bytes32(0),
            recipient: multisig1,
            value: 0,
            deadline: uint64(block.timestamp + 1800),
            signature: hex"0123456789abcdef"
        });

        vm.startPrank(multisig1);

        for (uint8 i = 0; i < numAttestations; i++) {
            tracker.attestByDelegation(request);
        }

        vm.stopPrank();

        assertEq(tracker.getNumAttestations(multisig1), numAttestations, "Attestation count should match");
    }



    // --- Gas Optimization Tests ---

    /**
     * @dev Test gas usage for attestation operations.
     * This helps ensure the contract is gas efficient.
     */
    function test_Gas_AttestByDelegation() public {
        IEAS.DelegatedAttestationRequest memory request = IEAS.DelegatedAttestationRequest({
            schema: bytes32(uint256(1)),
            data: abi.encode("test data"),
            expirationTime: uint64(block.timestamp + 3600),
            revocable: false,
            refUID: bytes32(0),
            recipient: multisig1,
            value: 0,
            deadline: uint64(block.timestamp + 1800),
            signature: hex"0123456789abcdef"
        });

        vm.prank(multisig1);
        uint256 gasBefore = gasleft();
        tracker.attestByDelegation(request);
        uint256 gasUsed = gasBefore - gasleft();

        console.log("Gas used for attestByDelegation:", gasUsed);

        // Should be reasonable gas usage
        assertLt(gasUsed, 150000, "Attestation should be gas efficient");
    }

    // --- Edge Case Tests ---

    /**
     * @dev Test attestation counter overflow protection.
     * This tests what happens when we try to increment past the maximum uint256.
     */
    function test_EdgeCase_AttestationCounterOverflow() public {
        // Set attestation count to maximum uint256
        uint256 maxCount = type(uint256).max;
        vm.store(address(tracker),
                keccak256(abi.encode(multisig1, 1)), // slot for mapMultisigAttestations[multisig1] (mapping is at slot 1)
                bytes32(maxCount));

        IEAS.DelegatedAttestationRequest memory request = IEAS.DelegatedAttestationRequest({
            schema: bytes32(uint256(1)),
            data: abi.encode("test data"),
            expirationTime: uint64(block.timestamp + 3600),
            revocable: false,
            refUID: bytes32(0),
            recipient: multisig1,
            value: 0,
            deadline: uint64(block.timestamp + 1800),
            signature: hex"0123456789abcdef"
        });

        // This should overflow and wrap to 0 in Solidity < 0.8.0 but revert in 0.8.0+
        vm.prank(multisig1);
        vm.expectRevert(); // Expect arithmetic overflow revert
        tracker.attestByDelegation(request);
    }
}
