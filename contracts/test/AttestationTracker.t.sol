// SPDX-License-Identifier: MIT
pragma solidity 0.8.24;

import {Test, console} from "forge-std/Test.sol";
import {AttestationTracker, IEAS_Fixed} from "../src/AttestationTracker.sol";

/**
 * @title MockEAS
 * @dev Mock EAS contract for testing purposes with correct interface.
 */
contract MockEAS {
    uint256 private _attestationCounter;

    mapping(bytes32 => bool) public attestations;

    function attestByDelegation(
        IEAS_Fixed.DelegatedAttestationRequest calldata
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

    // --- Attestation Wrapper Tests ---

    /**
     * @dev Test successful attestation through wrapper.
     * This tests the core attestation wrapper functionality that forwards to EAS
     * while incrementing the local attestation counter.
     */
    function test_AttestByDelegation_Success() public {
        vm.prank(multisig1);
        bytes32 attestationUID = tracker.attestByDelegation(
            bytes32(uint256(1)), // schema
            multisig1, // recipient
            uint64(block.timestamp + 3600), // expirationTime
            false, // revocable
            bytes32(0), // refUID
            abi.encode("test data"), // data
            0, // value
            27, // v
            bytes32(uint256(1)), // r
            bytes32(uint256(2)), // s
            multisig1, // attester
            uint64(block.timestamp + 1800) // deadline
        );

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
        vm.expectEmit(true, false, false, false);
        emit AttestationMade(multisig1, bytes32(0)); // Only check multisig address, ignore UID

        vm.prank(multisig1);
        tracker.attestByDelegation(
            bytes32(uint256(1)), // schema
            multisig1, // recipient
            uint64(block.timestamp + 3600), // expirationTime
            false, // revocable
            bytes32(0), // refUID
            abi.encode("test data"), // data
            0, // value
            27, // v
            bytes32(uint256(1)), // r
            bytes32(uint256(2)), // s
            multisig1, // attester
            uint64(block.timestamp + 1800) // deadline
        );
    }

    /**
     * @dev Test multiple attestations increment counter correctly.
     * This verifies that the attestation counter properly increments with each attestation.
     */
    function test_AttestByDelegation_MultipleAttestations() public {
        vm.startPrank(multisig1);

        // Make multiple attestations
        for (uint i = 0; i < 3; i++) {
            tracker.attestByDelegation(
                bytes32(uint256(1)), // schema
                multisig1, // recipient
                uint64(block.timestamp + 3600), // expirationTime
                false, // revocable
                bytes32(0), // refUID
                abi.encode("test data", i), // data
                0, // value
                27, // v
                bytes32(uint256(i + 1)), // r
                bytes32(uint256(i + 2)), // s
                multisig1, // attester
                uint64(block.timestamp + 1800) // deadline
            );
        }

        vm.stopPrank();

        assertEq(tracker.getNumAttestations(multisig1), 3, "Should have 3 attestations");
    }

    /**
     * @dev Test attestation with ETH value forwarding.
     * This ensures that ETH sent with attestations is properly forwarded to EAS.
     */
    function test_AttestByDelegation_WithValue() public {
        // Give multisig1 some ETH
        vm.deal(multisig1, 2 ether);

        uint256 initialBalance = address(mockEAS).balance;

        vm.prank(multisig1);
        tracker.attestByDelegation{value: 1 ether}(
            bytes32(uint256(1)), // schema
            multisig1, // recipient
            uint64(block.timestamp + 3600), // expirationTime
            false, // revocable
            bytes32(0), // refUID
            abi.encode("test data"), // data
            1 ether, // value
            27, // v
            bytes32(uint256(1)), // r
            bytes32(uint256(2)), // s
            multisig1, // attester
            uint64(block.timestamp + 1800) // deadline
        );

        // Verify ETH was forwarded to EAS
        assertEq(address(mockEAS).balance, initialBalance + 1 ether, "ETH should be forwarded to EAS");
    }

    // --- Multi-Multisig Independent Tracking Tests ---

    /**
     * @dev Test that different multisigs have independent attestation tracking.
     * This ensures that each multisig's attestations and status are tracked separately.
     */
    function test_IndependentMultisigs_AttestationTracking() public {
        // multisig1 makes 2 attestations
        vm.startPrank(multisig1);
        for (uint i = 0; i < 2; i++) {
            tracker.attestByDelegation(
                bytes32(uint256(1)), // schema
                multisig1, // recipient
                uint64(block.timestamp + 3600), // expirationTime
                false, // revocable
                bytes32(0), // refUID
                abi.encode("test data", i), // data
                0, // value
                27, // v
                bytes32(uint256(i + 1)), // r
                bytes32(uint256(i + 2)), // s
                multisig1, // attester
                uint64(block.timestamp + 1800) // deadline
            );
        }
        vm.stopPrank();

        // multisig2 makes 3 attestations
        vm.startPrank(multisig2);
        for (uint i = 0; i < 3; i++) {
            tracker.attestByDelegation(
                bytes32(uint256(2)), // schema
                multisig2, // recipient
                uint64(block.timestamp + 3600), // expirationTime
                false, // revocable
                bytes32(0), // refUID
                abi.encode("test data", i), // data
                0, // value
                27, // v
                bytes32(uint256(i + 10)), // r
                bytes32(uint256(i + 20)), // s
                multisig2, // attester
                uint64(block.timestamp + 1800) // deadline
            );
        }
        vm.stopPrank();

        // Verify independent tracking
        assertEq(tracker.getNumAttestations(multisig1), 2, "multisig1 should have 2 attestations");
        assertEq(tracker.getNumAttestations(multisig2), 3, "multisig2 should have 3 attestations");
    }

    // --- IQuorumTracker Interface Tests ---

    /**
     * @dev Test IQuorumTracker getVotingStats implementation.
     * This tests the new IQuorumTracker interface functionality.
     */
    function test_GetVotingStats_ReturnsCorrectFormat() public {
        // Make 3 attestations for multisig1
        vm.startPrank(multisig1);
        for (uint i = 0; i < 3; i++) {
            tracker.attestByDelegation(
                bytes32(uint256(1)), // schema
                multisig1, // recipient
                uint64(block.timestamp + 3600), // expirationTime
                false, // revocable
                bytes32(0), // refUID
                abi.encode("test data", i), // data
                0, // value
                27, // v
                bytes32(uint256(i + 1)), // r
                bytes32(uint256(i + 2)), // s
                multisig1, // attester
                uint64(block.timestamp + 1800) // deadline
            );
        }
        vm.stopPrank();

        uint256[] memory stats = tracker.getVotingStats(multisig1);
        
        assertEq(stats.length, 3, "Should return 3 elements");
        assertEq(stats[0], 3, "Casted votes should be 3");
        assertEq(stats[1], 3, "Voting opportunities should be 3");
        assertEq(stats[2], 0, "No voting opportunities should be 0");
    }

    // --- Edge Case Tests ---

    /**
     * @dev Test attestation counting at maximum value.
     * This tests the edge case where the counter reaches maximum uint256.
     */
    function test_AttestationCount_MaxValue() public {
        // Directly set the counter to max - 1 using vm.store
        vm.store(
            address(tracker),
            keccak256(abi.encode(multisig1, uint256(1))), // slot for mapMultisigAttestations[multisig1]
            bytes32(type(uint256).max - 1)
        );

        assertEq(tracker.getNumAttestations(multisig1), type(uint256).max - 1, "Counter should be at max - 1");

        // This should increment to max uint256
        vm.prank(multisig1);
        tracker.attestByDelegation(
            bytes32(uint256(1)), // schema
            multisig1, // recipient
            uint64(block.timestamp + 3600), // expirationTime
            false, // revocable
            bytes32(0), // refUID
            abi.encode("test data"), // data
            0, // value
            27, // v
            bytes32(uint256(1)), // r
            bytes32(uint256(2)), // s
            multisig1, // attester
            uint64(block.timestamp + 1800) // deadline
        );

        assertEq(tracker.getNumAttestations(multisig1), type(uint256).max, "Counter should be at max");
    }

    /**
     * @dev Test zero attestations.
     * This ensures the contract behaves correctly when no attestations have been made.
     */
    function test_ZeroAttestations() public view {
        assertEq(tracker.getNumAttestations(multisig1), 0, "Should have 0 attestations initially");
        assertEq(tracker.getNumAttestations(address(0)), 0, "Zero address should have 0 attestations");
    }

    // --- Gas Optimization Tests ---

    /**
     * @dev Test gas consumption for attestation operations.
     * This helps track and optimize gas usage over time.
     */
    function test_Gas_AttestByDelegation() public {
        vm.prank(multisig1);
        uint256 gasBefore = gasleft();
        tracker.attestByDelegation(
            bytes32(uint256(1)), // schema
            multisig1, // recipient
            uint64(block.timestamp + 3600), // expirationTime
            false, // revocable
            bytes32(0), // refUID
            abi.encode("test data"), // data
            0, // value
            27, // v
            bytes32(uint256(1)), // r
            bytes32(uint256(2)), // s
            multisig1, // attester
            uint64(block.timestamp + 1800) // deadline
        );
        uint256 gasUsed = gasBefore - gasleft();

        console.log("Gas used for attestByDelegation:", gasUsed);
        // Gas should be reasonable (adjust threshold as needed)
        assertLt(gasUsed, 150000, "Gas usage should be reasonable");
    }

    /**
     * @dev Test gas consumption for view functions.
     */
    function test_Gas_ViewFunctions() public {
        // Setup: Make some attestations
        vm.prank(multisig1);
        tracker.attestByDelegation(
            bytes32(uint256(1)), // schema
            multisig1, // recipient
            uint64(block.timestamp + 3600), // expirationTime
            false, // revocable
            bytes32(0), // refUID
            abi.encode("test data"), // data
            0, // value
            27, // v
            bytes32(uint256(1)), // r
            bytes32(uint256(2)), // s
            multisig1, // attester
            uint64(block.timestamp + 1800) // deadline
        );

        // Test getNumAttestations gas
        uint256 gasBefore = gasleft();
        tracker.getNumAttestations(multisig1);
        uint256 gasUsed = gasBefore - gasleft();

        console.log("Gas used for getNumAttestations:", gasUsed);
        assertLt(gasUsed, 5000, "View function should be cheap");

        // Test getVotingStats gas
        gasBefore = gasleft();
        tracker.getVotingStats(multisig1);
        gasUsed = gasBefore - gasleft();

        console.log("Gas used for getVotingStats:", gasUsed);
        assertLt(gasUsed, 10000, "View function should be relatively cheap");
    }

    // --- Fuzz Testing ---

    /**
     * @dev Fuzz test for attestation counting.
     * This ensures the counter works correctly with random inputs.
     */
    function testFuzz_AttestationCounting(address multisig, uint8 numAttestations) public {
        vm.assume(multisig != address(0));
        vm.assume(numAttestations > 0 && numAttestations <= 100); // Reasonable range

        vm.startPrank(multisig);
        for (uint8 i = 0; i < numAttestations; i++) {
            tracker.attestByDelegation(
                bytes32(uint256(i)), // schema
                multisig, // recipient
                uint64(block.timestamp + 3600), // expirationTime
                false, // revocable
                bytes32(0), // refUID
                abi.encode("test data", i), // data
                0, // value
                27, // v
                bytes32(uint256(i + 1)), // r
                bytes32(uint256(i + 2)), // s
                multisig, // attester
                uint64(block.timestamp + 1800) // deadline
            );
        }
        vm.stopPrank();

        assertEq(tracker.getNumAttestations(multisig), numAttestations, "Counter should match number of attestations");
    }

    /**
     * @dev Fuzz test for multiple multisigs with independent tracking.
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

        // MultisigA attestations
        vm.startPrank(multisigA);
        for (uint8 i = 0; i < countA; i++) {
            tracker.attestByDelegation(
                bytes32(uint256(i)), // schema
                multisigA, // recipient
                uint64(block.timestamp + 3600), // expirationTime
                false, // revocable
                bytes32(0), // refUID
                abi.encode("test data A", i), // data
                0, // value
                27, // v
                bytes32(uint256(i + 1)), // r
                bytes32(uint256(i + 2)), // s
                multisigA, // attester
                uint64(block.timestamp + 1800) // deadline
            );
        }
        vm.stopPrank();

        // MultisigB attestations
        vm.startPrank(multisigB);
        for (uint8 i = 0; i < countB; i++) {
            tracker.attestByDelegation(
                bytes32(uint256(i + 100)), // schema
                multisigB, // recipient
                uint64(block.timestamp + 3600), // expirationTime
                false, // revocable
                bytes32(0), // refUID
                abi.encode("test data B", i), // data
                0, // value
                27, // v
                bytes32(uint256(i + 100)), // r
                bytes32(uint256(i + 200)), // s
                multisigB, // attester
                uint64(block.timestamp + 1800) // deadline
            );
        }
        vm.stopPrank();

        assertEq(tracker.getNumAttestations(multisigA), countA, "MultisigA count should be correct");
        assertEq(tracker.getNumAttestations(multisigB), countB, "MultisigB count should be correct");
    }
}