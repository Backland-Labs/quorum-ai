// SPDX-License-Identifier: MIT
pragma solidity 0.8.24;

import "@openzeppelin/contracts/access/Ownable.sol";

/**
 * @title IEAS
 * @dev Interface for Ethereum Attestation Service interactions.
 */
interface IEAS {
    struct DelegatedAttestationRequest {
        bytes32 schema;
        bytes data;
        uint64 expirationTime;
        bool revocable;
        bytes32 refUID;
        address recipient;
        uint256 value;
        uint64 deadline;
        bytes signature;
    }

    function attestByDelegation(DelegatedAttestationRequest calldata request) external payable returns (bytes32);
}

/**
 * @title AttestationTracker
 * @dev Minimal implementation of the DualStakingToken attestation pattern.
 * 
 * This contract serves as a wrapper around EAS (Ethereum Attestation Service) 
 * that tracks which multisigs make attestations and maintains an active/inactive 
 * status for each multisig using efficient bit manipulation.
 * 
 * Key features:
 * - Tracks attestation count per multisig address
 * - Maintains active/inactive status per multisig
 * - Uses single storage slot per multisig (MSB = active status, lower 255 bits = count)
 * - Forwards all attestations to EAS while maintaining local tracking
 */
contract AttestationTracker is Ownable {
    // --- Events ---
    event AttestationMade(address indexed multisig, bytes32 indexed attestationUID);

    // --- Immutables ---
    /// @dev EAS contract address for attestation functionality
    address public immutable EAS;

    // --- State ---
    /// @dev Mapping of multisig addresses => (active status bit + attestation counter)
    /// Following DualStakingToken pattern: MSB = active status, lower 255 bits = attestation count
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
     * @notice Sets the active status for a multisig address.
     * @dev Can be used to mark multisigs as active/inactive for staking-related functionality.
     * Only the contract owner can call this function.
     * @param multisig The address of the multisig.
     * @param active True to mark as active, false to mark as inactive.
     */
    function setMultisigActiveStatus(address multisig, bool active) external onlyOwner {
        if (active) {
            // Set MSB to indicate active status, preserving attestation count
            mapMultisigAttestations[multisig] |= 1 << 255;
        } else {
            // Clear MSB while preserving attestation count
            mapMultisigAttestations[multisig] &= ((1 << 255) - 1);
        }
    }

    /**
     * @notice Wrapper function for EAS attestations that tracks which multisigs make attestations.
     * @dev This is the core wrapper functionality following the DualStakingToken pattern.
     * Increments the attestation counter for msg.sender and forwards the request to EAS.
     * @param delegatedRequest The EAS delegated attestation request.
     * @return attestationUID The UID of the created attestation.
     */
    function attestByDelegation(IEAS.DelegatedAttestationRequest calldata delegatedRequest) 
        external 
        payable 
        returns (bytes32 attestationUID) 
    {
        // Increment attestation counter for the caller (preserving upper bits)
        mapMultisigAttestations[msg.sender]++;
        
        // Forward the attestation request to EAS
        attestationUID = IEAS(EAS).attestByDelegation{value: msg.value}(delegatedRequest);
        
        emit AttestationMade(msg.sender, attestationUID);
        
        return attestationUID;
    }

    // --- View Functions ---
    
    /**
     * @notice Gets the number of attestations made by a multisig address.
     * @param multisig The address of the multisig.
     * @return The number of attestations made (excluding MSB active status).
     */
    function getNumAttestations(address multisig) external view returns (uint256) {
        // Remove MSB to get just the attestation count
        return mapMultisigAttestations[multisig] & ((1 << 255) - 1);
    }

    /**
     * @notice Checks if a multisig is marked as active.
     * @param multisig The address of the multisig.
     * @return True if the multisig is active, false otherwise.
     */
    function isMultisigActive(address multisig) external view returns (bool) {
        // Check MSB for active status
        return (mapMultisigAttestations[multisig] >> 255) == 1;
    }

    /**
     * @notice Gets both attestation count and active status for a multisig.
     * @dev More gas efficient than calling getNumAttestations and isMultisigActive separately.
     * @param multisig The address of the multisig.
     * @return numAttestations Number of attestations made.
     * @return isActive Whether the multisig is marked as active.
     */
    function getMultisigInfo(address multisig) 
        external 
        view 
        returns (uint256 numAttestations, bool isActive) 
    {
        uint256 attestationData = mapMultisigAttestations[multisig];
        numAttestations = attestationData & ((1 << 255) - 1);
        isActive = (attestationData >> 255) == 1;
    }
}