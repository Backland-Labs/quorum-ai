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
 * @dev Interface for Ethereum Attestation Service interactions.
 * This interface expects a single nested tuple parameter.
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
    
    struct Signature {
        uint8 v;
        bytes32 r;
        bytes32 s;
    }
    
    struct DelegatedAttestationRequest {
        bytes32 schema;
        AttestationRequestData data;
        Signature signature;
        address attester;
        uint64 deadline;
    }
    
    // The actual EAS interface expects a single nested tuple parameter
    function attestByDelegation(
        DelegatedAttestationRequest calldata delegatedRequest
    ) external payable returns (bytes32);
}

/**
 * @title AttestationTracker
 * @dev Attestation counter wrapper around EAS (Ethereum Attestation Service).
 *
 * This contract serves as a wrapper around EAS that tracks the number of
 * attestations made by each multisig address.
 *
 * Key features:
 * - Tracks attestation count per multisig address
 * - Simple uint256 counter for each multisig
 * - Accepts separate parameters (for backward compatibility with SafeService)
 * - Reconstructs the nested tuple structure before forwarding to EAS
 * - Uses the single-parameter EAS interface
 */
contract AttestationTracker is Ownable, IQuorumTracker {
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
        require(_EAS != address(0), "AttestationTracker: EAS address cannot be zero");
        EAS = _EAS;
    }

    // --- External Functions ---

    /**
     * @notice Wrapper function for EAS attestations that tracks which multisigs make attestations.
     * @dev Accepts 4 separate parameters for backward compatibility with SafeService,
     * then reconstructs the nested tuple structure before forwarding to EAS.
     * @param schema The schema UID for the attestation.
     * @param recipient The recipient of the attestation.
     * @param expirationTime The expiration time for the attestation.
     * @param revocable Whether the attestation is revocable.
     * @param refUID The reference UID for the attestation.
     * @param data The attestation data.
     * @param value The value sent with the attestation.
     * @param v The v component of the signature.
     * @param r The r component of the signature.
     * @param s The s component of the signature.
     * @param attester The address of the attester.
     * @param deadline The deadline for the attestation.
     * @return attestationUID The UID of the created attestation.
     */
    function attestByDelegation(
        bytes32 schema,
        address recipient,
        uint64 expirationTime,
        bool revocable,
        bytes32 refUID,
        bytes calldata data,
        uint256 value,
        uint8 v,
        bytes32 r,
        bytes32 s,
        address attester,
        uint64 deadline
    ) external payable returns (bytes32 attestationUID) {
        // Increment attestation counter for the caller
        mapMultisigAttestations[msg.sender]++;

        // Forward the attestation request to EAS with the single nested tuple parameter
        // Construct inline to avoid "stack too deep" error
        attestationUID = IEAS(EAS).attestByDelegation{value: msg.value}(
            IEAS.DelegatedAttestationRequest({
                schema: schema,
                data: IEAS.AttestationRequestData({
                    recipient: recipient,
                    expirationTime: expirationTime,
                    revocable: revocable,
                    refUID: refUID,
                    data: data,
                    value: value
                }),
                signature: IEAS.Signature({
                    v: v,
                    r: r,
                    s: s
                }),
                attester: attester,
                deadline: deadline
            })
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