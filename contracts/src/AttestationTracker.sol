// SPDX-License-Identifier: MIT
pragma solidity 0.8.24;

import "@openzeppelin/contracts/access/Ownable.sol";

/**
 * @title IQuorumTracker
 * @dev Interface for tracking voting statistics.
 */
interface IQuorumTracker {
    function getVotingStats(address multisig) external view returns (uint256[] memory votingStats);
}

/**
 * @title IEAS
 * @dev CORRECT Interface for Ethereum Attestation Service interactions.
 */
interface IEAS {
    struct AttestationRequestData {
        address recipient;
        uint64 expirationTime;
        bool revocable;
        bytes32 refUID;
        bytes data;
        uint256 value;
    }
    
    struct DelegatedAttestationRequest {
        bytes32 schema;
        AttestationRequestData data;
    }
    
    struct Signature {
        uint8 v;
        bytes32 r;
        bytes32 s;
    }
    
    function attestByDelegation(
        DelegatedAttestationRequest calldata delegatedRequest,
        Signature calldata signature,
        address attester,
        uint64 deadline
    ) external payable returns (bytes32);
}

/**
 * @title AttestationTrackerFixed
 * @dev CORRECTED attestation counter wrapper around EAS (Ethereum Attestation Service).
 *
 * This contract serves as a wrapper around EAS that tracks the number of
 * attestations made by each multisig address, using the CORRECT EAS interface.
 *
 * Key features:
 * - Tracks attestation count per multisig address
 * - Simple uint256 counter for each multisig
 * - Forwards all attestations to EAS with correct parameters
 */
contract AttestationTrackerFixed is Ownable, IQuorumTracker {
    // --- Events ---
    event AttestationMade(address indexed multisig, bytes32 indexed attestationUID);

    // --- Immutables ---
    /// @dev EAS contract address for attestation functionality
    address public immutable EAS;

    // --- State ---
    /// @dev Mapping of multisig addresses => attestation counter
    mapping(address => uint256) public mapMultisigAttestations;

    // --- Constructor ---
    /**
     * @dev Sets the initial owner and EAS contract address.
     * @param initialOwner The address of the initial owner.
     * @param _EAS The EAS contract address for attestation functionality.
     */
    constructor(address initialOwner, address _EAS) Ownable(initialOwner) {
        require(_EAS != address(0), "AttestationTrackerFixed: EAS address cannot be zero");
        EAS = _EAS;
    }

    // --- External Functions ---

    /**
     * @notice Wrapper function for EAS attestations that tracks which multisigs make attestations.
     * @dev Increments the attestation counter for msg.sender and forwards the request to EAS.
     * @param delegatedRequest The EAS delegated attestation request.
     * @param signature The signature for the attestation.
     * @param attester The address of the attester.
     * @param deadline The deadline for the attestation.
     * @return attestationUID The UID of the created attestation.
     */
    function attestByDelegation(
        IEAS.DelegatedAttestationRequest calldata delegatedRequest,
        IEAS.Signature calldata signature,
        address attester,
        uint64 deadline
    ) external payable returns (bytes32 attestationUID) {
        // Increment attestation counter for the caller
        mapMultisigAttestations[msg.sender]++;

        // Forward the attestation request to EAS with all required parameters
        attestationUID = IEAS(EAS).attestByDelegation{value: msg.value}(
            delegatedRequest,
            signature,
            attester,
            deadline
        );

        emit AttestationMade(msg.sender, attestationUID);

        return attestationUID;
    }

    // --- View Functions ---

    /**
     * @notice Gets the number of attestations made by a multisig address.
     * @param multisig The address of the multisig.
     * @return The number of attestations made.
     */
    function getNumAttestations(address multisig) external view returns (uint256) {
        return mapMultisigAttestations[multisig];
    }

    /**
     * @notice Gets voting statistics for a multisig address.
     * @dev Implementation of IQuorumTracker interface.
     * @param multisig The address of the multisig.
     * @return votingStats Array containing [casted votes, voting opportunities, no voting opportunities].
     */
    function getVotingStats(address multisig) external view returns (uint256[] memory votingStats) {
        votingStats = new uint256[](3);
        uint256 attestationCount = mapMultisigAttestations[multisig];

        // [0]: attestations for casted votes (use current attestation count)
        votingStats[0] = attestationCount;
        // [1]: attestations for voting opportunities (use current attestation count)
        votingStats[1] = attestationCount;
        // [2]: attestations for no voting opportunities (return 0 for now)
        votingStats[2] = 0;

        return votingStats;
    }
}