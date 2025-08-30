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
 * - Bit manipulation for efficient storage (active status + attestation count)
 * - Access control for owner-only functions
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

        // Initial states should be zero
        assertEq(tracker.getNumAttestations(multisig1), 0, "Initial attestation count should be 0");
        assertFalse(tracker.isMultisigActive(multisig1), "Initial active status should be false");
    }

    // --- Active Status Management Tests ---

    /**
     * @dev Test setting multisig active status as owner.
     * This tests the core active status toggle functionality.
     */
    function test_SetMultisigActiveStatus_AsOwner() public {
        // Initially inactive
        assertFalse(tracker.isMultisigActive(multisig1), "Should be initially inactive");

        // Set active
        vm.prank(owner);
        tracker.setMultisigActiveStatus(multisig1, true);
        assertTrue(tracker.isMultisigActive(multisig1), "Should be active after setting");

        // Set inactive
        vm.prank(owner);
        tracker.setMultisigActiveStatus(multisig1, false);
        assertFalse(tracker.isMultisigActive(multisig1), "Should be inactive after clearing");
    }

    /**
     * @dev Test that only owner can set active status.
     * This ensures proper access control for administrative functions.
     */
    function test_RevertWhen_SetMultisigActiveStatus_NotOwner() public {
        vm.prank(unauthorized);
        vm.expectRevert("Ownable: caller is not the owner");
        tracker.setMultisigActiveStatus(multisig1, true);
    }

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

    // --- Bit Manipulation Tests ---

    /**
     * @dev Test that active status and attestation count work independently.
     * This is crucial for testing the DualStakingToken pattern's bit manipulation.
     */
    function test_BitManipulation_ActiveStatusAndAttestations() public {
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

        // Make attestation first
        vm.prank(multisig1);
        tracker.attestByDelegation(request);

        assertEq(tracker.getNumAttestations(multisig1), 1, "Should have 1 attestation");
        assertFalse(tracker.isMultisigActive(multisig1), "Should not be active yet");

        // Set active status
        vm.prank(owner);
        tracker.setMultisigActiveStatus(multisig1, true);

        assertEq(tracker.getNumAttestations(multisig1), 1, "Attestation count should be preserved");
        assertTrue(tracker.isMultisigActive(multisig1), "Should be active now");

        // Make another attestation
        vm.prank(multisig1);
        tracker.attestByDelegation(request);

        assertEq(tracker.getNumAttestations(multisig1), 2, "Should have 2 attestations now");
        assertTrue(tracker.isMultisigActive(multisig1), "Should still be active");

        // Set inactive
        vm.prank(owner);
        tracker.setMultisigActiveStatus(multisig1, false);

        assertEq(tracker.getNumAttestations(multisig1), 2, "Attestation count should be preserved");
        assertFalse(tracker.isMultisigActive(multisig1), "Should be inactive now");
    }

    /**
     * @dev Test the combined getter function for gas efficiency.
     * This tests getMultisigInfo which returns both values in a single call.
     */
    function test_GetMultisigInfo_Efficiency() public {
        // Set up some state
        vm.prank(owner);
        tracker.setMultisigActiveStatus(multisig1, true);

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
        tracker.attestByDelegation(request);
        tracker.attestByDelegation(request);
        vm.stopPrank();

        // Get info with single call
        (uint256 numAttestations, bool isActive) = tracker.getMultisigInfo(multisig1);

        assertEq(numAttestations, 2, "Should have 2 attestations");
        assertTrue(isActive, "Should be active");
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

        // Set multisig1 as active
        vm.prank(owner);
        tracker.setMultisigActiveStatus(multisig1, true);

        // Verify independent tracking
        assertEq(tracker.getNumAttestations(multisig1), 2, "Multisig1 should have 2 attestations");
        assertEq(tracker.getNumAttestations(multisig2), 1, "Multisig2 should have 1 attestation");
        assertTrue(tracker.isMultisigActive(multisig1), "Multisig1 should be active");
        assertFalse(tracker.isMultisigActive(multisig2), "Multisig2 should not be active");
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

    /**
     * @dev Fuzz test for active status toggling with attestations.
     * This ensures that active status changes don't affect attestation counts.
     */
    function testFuzz_ActiveStatusToggling(uint8 numAttestations, bool finalActiveState) public {
        vm.assume(numAttestations > 0 && numAttestations <= 50);

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

        // Make attestations
        vm.startPrank(multisig1);
        for (uint8 i = 0; i < numAttestations; i++) {
            tracker.attestByDelegation(request);
        }
        vm.stopPrank();

        // Toggle active status multiple times
        vm.startPrank(owner);
        tracker.setMultisigActiveStatus(multisig1, true);
        tracker.setMultisigActiveStatus(multisig1, false);
        tracker.setMultisigActiveStatus(multisig1, true);
        tracker.setMultisigActiveStatus(multisig1, finalActiveState);
        vm.stopPrank();

        // Verify attestation count is preserved through all toggles
        assertEq(tracker.getNumAttestations(multisig1), numAttestations, "Attestation count should be preserved");
        assertEq(tracker.isMultisigActive(multisig1), finalActiveState, "Final active state should match");
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
     * @dev Test maximum attestation counter (near 2^255-1).
     * This tests the edge case of the bit manipulation pattern.
     */
    function test_EdgeCase_MaxAttestationCount() public {
        // We can't test the actual maximum due to gas limits, but we can test the bit manipulation
        uint256 maxCount = (1 << 255) - 1;

        // Directly set a high attestation count via storage manipulation for testing
        // This simulates having a very high attestation count
        vm.store(address(tracker),
                keccak256(abi.encode(multisig1, 1)), // slot for mapMultisigAttestations[multisig1] (mapping is at slot 1)
                bytes32(maxCount));

        assertEq(tracker.getNumAttestations(multisig1), maxCount, "Should handle max attestation count");
        assertFalse(tracker.isMultisigActive(multisig1), "Should not be active with max count");

        // Set active status
        vm.prank(owner);
        tracker.setMultisigActiveStatus(multisig1, true);

        assertEq(tracker.getNumAttestations(multisig1), maxCount, "Count should be preserved");
        assertTrue(tracker.isMultisigActive(multisig1), "Should be active");
    }

    /**
     * @dev Test attestation counter overflow protection.
     * This tests what happens when we try to increment past the maximum.
     */
    function test_EdgeCase_AttestationCounterOverflow() public {
        // Set attestation count to maximum (2^255 - 1)
        uint256 maxCount = (1 << 255) - 1;
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

        // This should overflow and wrap to 0 (with MSB potentially set)
        vm.prank(multisig1);
        tracker.attestByDelegation(request);

        // The attestation count should have wrapped around
        // Due to the bit manipulation, this will interfere with the active status bit
        uint256 finalCount = tracker.getNumAttestations(multisig1);

        // This is an edge case - in practice, reaching 2^255 attestations is impossible
        // but we test to understand the behavior
        console.log("Attestation count after overflow:", finalCount);
    }
}
