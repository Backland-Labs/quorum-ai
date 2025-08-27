// SPDX-License-Identifier: MIT
pragma solidity 0.8.24;

import {Test, console} from "forge-std/Test.sol";
import {QuorumTracker} from "../src/QuorumTracker.sol";

/**
 * @title QuorumTrackerTest
 * @dev Comprehensive test suite for the QuorumTracker contract.
 * Tests include unit tests, access control, edge cases, and fuzz testing.
 */
contract QuorumTrackerTest is Test {
    QuorumTracker public quorumTracker;
    
    // Test addresses
    address public owner = makeAddr("owner");
    address public multisig1 = makeAddr("multisig1");
    address public multisig2 = makeAddr("multisig2");
    address public unauthorized = makeAddr("unauthorized");

    // Events for testing (if needed in future versions)
    event ActivityRegistered(address indexed multisig, uint8 activityType, uint256 newCount);

    /**
     * @dev Sets up the test environment before each test.
     * Deploys a new QuorumTracker contract with the test owner.
     */
    function setUp() public {
        // Deploy the contract with owner as the initial owner
        quorumTracker = new QuorumTracker(owner);
        
        // Verify initial setup
        assertEq(quorumTracker.owner(), owner, "Owner should be set correctly");
        assertEq(quorumTracker.VOTES_CAST(), 0, "VOTES_CAST should be 0");
        assertEq(quorumTracker.OPPORTUNITIES_CONSIDERED(), 1, "OPPORTUNITIES_CONSIDERED should be 1");
        assertEq(quorumTracker.NO_OPPORTUNITIES(), 2, "NO_OPPORTUNITIES should be 2");
    }

    // --- Constructor Tests ---
    
    /**
     * @dev Test that constructor sets owner correctly.
     */
    function test_Constructor_SetsOwnerCorrectly() public {
        address testOwner = makeAddr("testOwner");
        QuorumTracker testTracker = new QuorumTracker(testOwner);
        
        assertEq(testTracker.owner(), testOwner, "Owner should be set to constructor parameter");
    }

    /**
     * @dev Test that constructor rejects zero address as owner.
     */
    function test_RevertWhen_Constructor_ZeroOwner() public {
        vm.expectRevert("Ownable: new owner is the zero address");
        new QuorumTracker(address(0));
    }

    // --- Activity Registration Tests ---

    /**
     * @dev Test successful activity registration as owner for NO_OPPORTUNITIES.
     */
    function test_RegisterActivity_NoOpportunities_AsOwner() public {
        uint8 noOpportunities = quorumTracker.NO_OPPORTUNITIES();
        
        vm.prank(owner);
        quorumTracker.register(multisig1, noOpportunities);
        
        uint256[] memory stats = quorumTracker.getVotingStats(multisig1);
        assertEq(stats[0], 0, "Votes cast should be 0");
        assertEq(stats[1], 0, "Opportunities considered should be 0");
        assertEq(stats[2], 1, "No opportunities should be 1");
    }

    /**
     * @dev Test successful activity registration as owner for OPPORTUNITIES_CONSIDERED.
     */
    function test_RegisterActivity_OpportunitiesConsidered_AsOwner() public {
        uint8 opportunitiesConsidered = quorumTracker.OPPORTUNITIES_CONSIDERED();
        
        vm.prank(owner);
        quorumTracker.register(multisig1, opportunitiesConsidered);
        
        uint256[] memory stats = quorumTracker.getVotingStats(multisig1);
        assertEq(stats[0], 0, "Votes cast should be 0");
        assertEq(stats[1], 1, "Opportunities considered should be 1");
        assertEq(stats[2], 0, "No opportunities should be 0");
    }

    /**
     * @dev Test successful activity registration as owner for VOTES_CAST.
     */
    function test_RegisterActivity_VotesCast_AsOwner() public {
        uint8 votesCast = quorumTracker.VOTES_CAST();
        
        vm.prank(owner);
        quorumTracker.register(multisig1, votesCast);
        
        uint256[] memory stats = quorumTracker.getVotingStats(multisig1);
        assertEq(stats[0], 1, "Votes cast should be 1");
        assertEq(stats[1], 0, "Opportunities considered should be 0");
        assertEq(stats[2], 0, "No opportunities should be 0");
    }

    /**
     * @dev Test that only owner can register activities.
     */
    function test_RevertWhen_RegisterActivity_NotOwner() public {
        uint8 votesCast = quorumTracker.VOTES_CAST();
        
        vm.prank(unauthorized);
        vm.expectRevert("Ownable: caller is not the owner");
        quorumTracker.register(multisig1, votesCast);
    }

    /**
     * @dev Test that invalid activity types are rejected.
     */
    function test_RevertWhen_RegisterActivity_InvalidActivityType() public {
        vm.prank(owner);
        vm.expectRevert("QuorumTracker: Invalid activity type");
        quorumTracker.register(multisig1, 3);
    }

    /**
     * @dev Test that activity type 255 (max uint8) is rejected.
     */
    function test_RevertWhen_RegisterActivity_MaxUint8ActivityType() public {
        vm.prank(owner);
        vm.expectRevert("QuorumTracker: Invalid activity type");
        quorumTracker.register(multisig1, 255);
    }

    // --- Multiple Registration Tests ---

    /**
     * @dev Test multiple registrations of the same activity type increment correctly.
     */
    function test_RegisterActivity_MultipleRegistrations_SameType() public {
        vm.startPrank(owner);
        
        // Register votes cast multiple times
        quorumTracker.register(multisig1, quorumTracker.VOTES_CAST());
        quorumTracker.register(multisig1, quorumTracker.VOTES_CAST());
        quorumTracker.register(multisig1, quorumTracker.VOTES_CAST());
        
        vm.stopPrank();
        
        uint256[] memory stats = quorumTracker.getVotingStats(multisig1);
        assertEq(stats[0], 3, "Votes cast should be 3");
        assertEq(stats[1], 0, "Opportunities considered should be 0");
        assertEq(stats[2], 0, "No opportunities should be 0");
    }

    /**
     * @dev Test multiple registrations of different activity types.
     */
    function test_RegisterActivity_MultipleRegistrations_DifferentTypes() public {
        vm.startPrank(owner);
        
        // Register different activities
        quorumTracker.register(multisig1, quorumTracker.VOTES_CAST());
        quorumTracker.register(multisig1, quorumTracker.VOTES_CAST());
        quorumTracker.register(multisig1, quorumTracker.OPPORTUNITIES_CONSIDERED());
        quorumTracker.register(multisig1, quorumTracker.NO_OPPORTUNITIES());
        
        vm.stopPrank();
        
        uint256[] memory stats = quorumTracker.getVotingStats(multisig1);
        assertEq(stats[0], 2, "Votes cast should be 2");
        assertEq(stats[1], 1, "Opportunities considered should be 1");
        assertEq(stats[2], 1, "No opportunities should be 1");
    }

    // --- Multiple Multisig Tests ---

    /**
     * @dev Test that different multisigs have independent statistics.
     */
    function test_RegisterActivity_DifferentMultisigs_IndependentStats() public {
        vm.startPrank(owner);
        
        // Register activities for different multisigs
        quorumTracker.register(multisig1, quorumTracker.VOTES_CAST());
        quorumTracker.register(multisig2, quorumTracker.OPPORTUNITIES_CONSIDERED());
        
        vm.stopPrank();
        
        uint256[] memory stats1 = quorumTracker.getVotingStats(multisig1);
        uint256[] memory stats2 = quorumTracker.getVotingStats(multisig2);
        
        // Verify multisig1 stats
        assertEq(stats1[0], 1, "Multisig1 votes cast should be 1");
        assertEq(stats1[1], 0, "Multisig1 opportunities considered should be 0");
        assertEq(stats1[2], 0, "Multisig1 no opportunities should be 0");
        
        // Verify multisig2 stats
        assertEq(stats2[0], 0, "Multisig2 votes cast should be 0");
        assertEq(stats2[1], 1, "Multisig2 opportunities considered should be 1");
        assertEq(stats2[2], 0, "Multisig2 no opportunities should be 0");
    }

    // --- Statistics Retrieval Tests ---

    /**
     * @dev Test getting statistics for unregistered multisig returns zeros.
     */
    function test_GetVotingStats_UnregisteredMultisig_ReturnsZeros() public {
        address unregisteredMultisig = makeAddr("unregistered");
        uint256[] memory stats = quorumTracker.getVotingStats(unregisteredMultisig);
        
        assertEq(stats.length, 3, "Stats array should have 3 elements");
        assertEq(stats[0], 0, "Votes cast should be 0");
        assertEq(stats[1], 0, "Opportunities considered should be 0");
        assertEq(stats[2], 0, "No opportunities should be 0");
    }

    /**
     * @dev Test getting statistics for zero address.
     */
    function test_GetVotingStats_ZeroAddress_ReturnsZeros() public {
        uint256[] memory stats = quorumTracker.getVotingStats(address(0));
        
        assertEq(stats.length, 3, "Stats array should have 3 elements");
        assertEq(stats[0], 0, "Votes cast should be 0");
        assertEq(stats[1], 0, "Opportunities considered should be 0");
        assertEq(stats[2], 0, "No opportunities should be 0");
    }

    /**
     * @dev Test that statistics retrieval is public and can be called by anyone.
     */
    function test_GetVotingStats_PublicAccess() public {
        // Register activity as owner
        uint8 votesCast = quorumTracker.VOTES_CAST();
        
        vm.prank(owner);
        quorumTracker.register(multisig1, votesCast);
        
        // Get stats as unauthorized user - should work
        vm.prank(unauthorized);
        uint256[] memory stats = quorumTracker.getVotingStats(multisig1);
        
        assertEq(stats.length, 3, "Stats array should have 3 elements");
        assertEq(stats[0], 1, "Votes cast should be 1");
        assertEq(stats[1], 0, "Opportunities considered should be 0");
        assertEq(stats[2], 0, "No opportunities should be 0");
    }

    // --- Direct Stats Mapping Access Tests ---

    /**
     * @dev Test direct access to stats mapping.
     */
    function test_StatsMapping_DirectAccess() public {
        uint8 votesCastType = quorumTracker.VOTES_CAST();
        
        vm.prank(owner);
        quorumTracker.register(multisig1, votesCastType);
        
        // Direct access to mapping
        uint256 votesCast = quorumTracker.stats(multisig1, 0);
        uint256 opportunities = quorumTracker.stats(multisig1, 1);
        uint256 noOpportunities = quorumTracker.stats(multisig1, 2);
        
        assertEq(votesCast, 1, "Direct access to votes cast should work");
        assertEq(opportunities, 0, "Direct access to opportunities should work");
        assertEq(noOpportunities, 0, "Direct access to no opportunities should work");
    }

    // --- Fuzz Tests ---

    /**
     * @dev Fuzz test for valid activity type registration.
     */
    function testFuzz_RegisterActivity_ValidActivityTypes(uint8 activityType) public {
        vm.assume(activityType <= quorumTracker.NO_OPPORTUNITIES());
        
        vm.prank(owner);
        quorumTracker.register(multisig1, activityType);
        
        uint256[] memory stats = quorumTracker.getVotingStats(multisig1);
        assertEq(stats[activityType], 1, "Activity should be incremented");
        
        // Verify other stats remain zero
        for (uint8 i = 0; i <= quorumTracker.NO_OPPORTUNITIES(); i++) {
            if (i != activityType) {
                assertEq(stats[i], 0, "Other activities should remain zero");
            }
        }
    }

    /**
     * @dev Fuzz test for invalid activity type registration.
     */
    function testFuzz_RevertWhen_RegisterActivity_InvalidActivityType(uint8 activityType) public {
        vm.assume(activityType > quorumTracker.NO_OPPORTUNITIES());
        
        vm.prank(owner);
        vm.expectRevert("QuorumTracker: Invalid activity type");
        quorumTracker.register(multisig1, activityType);
    }

    /**
     * @dev Fuzz test for multiple registrations with valid activity types.
     */
    function testFuzz_RegisterActivity_MultipleRegistrations(
        uint8 activityType, 
        uint8 registrationCount
    ) public {
        vm.assume(activityType <= quorumTracker.NO_OPPORTUNITIES());
        vm.assume(registrationCount > 0 && registrationCount <= 100); // Reasonable bounds
        
        vm.startPrank(owner);
        
        for (uint8 i = 0; i < registrationCount; i++) {
            quorumTracker.register(multisig1, activityType);
        }
        
        vm.stopPrank();
        
        uint256[] memory stats = quorumTracker.getVotingStats(multisig1);
        assertEq(stats[activityType], registrationCount, "Activity count should match registrations");
    }

    /**
     * @dev Fuzz test for different multisig addresses.
     */
    function testFuzz_RegisterActivity_DifferentMultisigs(
        address multisigAddr,
        uint8 activityType
    ) public {
        vm.assume(multisigAddr != address(0));
        vm.assume(activityType <= quorumTracker.NO_OPPORTUNITIES());
        
        vm.prank(owner);
        quorumTracker.register(multisigAddr, activityType);
        
        uint256[] memory stats = quorumTracker.getVotingStats(multisigAddr);
        assertEq(stats[activityType], 1, "Activity should be registered for any valid address");
    }

    // --- Gas Optimization Tests ---

    /**
     * @dev Test gas usage for registration operations.
     */
    function test_Gas_RegisterActivity() public {
        uint8 votesCast = quorumTracker.VOTES_CAST();
        
        vm.prank(owner);
        uint256 gasBefore = gasleft();
        quorumTracker.register(multisig1, votesCast);
        uint256 gasUsed = gasBefore - gasleft();
        
        // Log gas usage for optimization tracking
        console.log("Gas used for register:", gasUsed);
        
        // Should be relatively low gas usage for simple counter increment
        assertLt(gasUsed, 60000, "Registration should be gas efficient");
    }

    /**
     * @dev Test gas usage for statistics retrieval.
     */
    function test_Gas_GetVotingStats() public {
        // Setup some stats first
        uint8 votesCast = quorumTracker.VOTES_CAST();
        uint8 opportunitiesConsidered = quorumTracker.OPPORTUNITIES_CONSIDERED();
        
        vm.startPrank(owner);
        quorumTracker.register(multisig1, votesCast);
        quorumTracker.register(multisig1, opportunitiesConsidered);
        vm.stopPrank();
        
        uint256 gasBefore = gasleft();
        quorumTracker.getVotingStats(multisig1);
        uint256 gasUsed = gasBefore - gasleft();
        
        console.log("Gas used for getVotingStats:", gasUsed);
        
        // Should be relatively low gas usage for simple array creation
        assertLt(gasUsed, 30000, "Stats retrieval should be gas efficient");
    }

    // --- Edge Case Tests ---

    /**
     * @dev Test behavior with maximum uint256 counter values (simulated).
     * Note: We can't actually test overflow since it would require too many transactions.
     */
    function test_RegisterActivity_HighCounterValues() public {
        vm.startPrank(owner);
        
        // Register activities many times to test higher counter values
        for (uint i = 0; i < 1000; i++) {
            quorumTracker.register(multisig1, quorumTracker.VOTES_CAST());
        }
        
        vm.stopPrank();
        
        uint256[] memory stats = quorumTracker.getVotingStats(multisig1);
        assertEq(stats[0], 1000, "High counter values should work correctly");
    }

    /**
     * @dev Test contract state consistency after many operations.
     */
    function test_StateConsistency_ManyOperations() public {
        vm.startPrank(owner);
        
        uint256 expectedVotes = 0;
        uint256 expectedOpportunities = 0;
        uint256 expectedNoOpportunities = 0;
        
        // Perform many mixed operations
        for (uint i = 0; i < 100; i++) {
            uint8 activityType = uint8(i % 3);
            quorumTracker.register(multisig1, activityType);
            
            if (activityType == 0) expectedVotes++;
            else if (activityType == 1) expectedOpportunities++;
            else expectedNoOpportunities++;
        }
        
        vm.stopPrank();
        
        uint256[] memory stats = quorumTracker.getVotingStats(multisig1);
        assertEq(stats[0], expectedVotes, "Votes cast count should be consistent");
        assertEq(stats[1], expectedOpportunities, "Opportunities count should be consistent");
        assertEq(stats[2], expectedNoOpportunities, "No opportunities count should be consistent");
    }
}