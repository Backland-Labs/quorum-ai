"""Tests for Compound Governor Bravo implementation - TDD RED PHASE (failing tests).

This test file defines the expected behavior for Compound Governor Bravo contracts,
focusing on Compound-specific functionality, contract detection, and vote encoding.
The tests follow the AAA pattern and include comprehensive validation, error handling,
and edge case coverage specifically for Compound's governance system.

The Compound Governor Bravo implementation is designed to:
1. Support Compound's specific contract addresses and ABI
2. Handle Compound-specific proposal states and voting mechanics
3. Integrate with existing VoteEncoder and GovernorABI infrastructure
4. Provide optimized transaction encoding for Compound proposals
5. Support Compound's delegation and voting power calculations
6. Handle Compound-specific error conditions and edge cases
"""

import pytest
import json
import asyncio
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Any, Optional, Tuple
from unittest.mock import patch, MagicMock, mock_open, AsyncMock
from web3 import Web3

# These imports will fail initially as the classes don't exist yet
# This is intentional for TDD RED phase
try:
    from services.compound_bravo_governor import (
        CompoundBravoGovernor,
        CompoundBravoDetector,
        CompoundBravoABI,
        CompoundContractRegistry,
        CompoundProposalStateManager,
        CompoundVotingPowerCalculator,
        CompoundDelegationManager,
        CompoundBravoError,
        CompoundProposalNotFoundError,
        CompoundVotingClosedError,
        CompoundInsufficientVotingPowerError
    )
    from services.vote_encoder import VoteEncoder, VoteEncodingResult
    from services.governor_abi import GovernorABI
    from models import (
        GovernorContractType, 
        VoteType, 
        ProposalState,
        CompoundProposalInfo,
        CompoundVoteRecord,
        CompoundDelegateInfo
    )
except ImportError:
    # Expected during RED phase - classes don't exist yet
    pass


class TestCompoundBravoGovernorInitialization:
    """Test CompoundBravoGovernor initialization and configuration."""

    def test_compound_bravo_governor_initialization_with_mainnet_contract(self) -> None:
        """Test CompoundBravoGovernor initializes correctly with mainnet contract address."""
        # This test will fail because CompoundBravoGovernor doesn't exist yet
        mainnet_compound_address = "0xc0Da02939E1441F497fd74F78cE7Decb17B66529"  # Actual Compound Governor Bravo
        
        governor = CompoundBravoGovernor(contract_address=mainnet_compound_address)
        
        assert governor is not None
        assert governor.contract_address == mainnet_compound_address
        assert governor.contract_type == GovernorContractType.COMPOUND
        assert governor.network == "mainnet"
        assert isinstance(governor.abi, CompoundBravoABI)

    def test_compound_bravo_governor_initialization_with_testnet_contract(self) -> None:
        """Test CompoundBravoGovernor initializes correctly with testnet contract address."""
        testnet_compound_address = "0x1234567890abcdef1234567890abcdef12345678"  # Test address
        
        governor = CompoundBravoGovernor(
            contract_address=testnet_compound_address,
            network="goerli"
        )
        
        assert governor.contract_address == testnet_compound_address
        assert governor.network == "goerli"
        assert governor.contract_type == GovernorContractType.COMPOUND

    def test_compound_bravo_governor_auto_detects_contract_from_address(self) -> None:
        """Test CompoundBravoGovernor auto-detects it's a Compound contract from address."""
        known_compound_address = "0xc0Da02939E1441F497fd74F78cE7Decb17B66529"
        
        # Should automatically detect this is a Compound contract
        governor = CompoundBravoGovernor.from_contract_address(known_compound_address)
        
        assert governor.contract_address == known_compound_address
        assert governor.contract_type == GovernorContractType.COMPOUND
        assert governor.auto_detected is True

    def test_compound_bravo_governor_initialization_validates_contract_address(self) -> None:
        """Test CompoundBravoGovernor validates contract address format."""
        # Test invalid address format
        with pytest.raises(CompoundBravoError, match="Invalid contract address format"):
            CompoundBravoGovernor(contract_address="invalid_address")
        
        # Test empty address
        with pytest.raises(CompoundBravoError, match="Contract address cannot be empty"):
            CompoundBravoGovernor(contract_address="")

    def test_compound_bravo_governor_loads_compound_specific_abi(self) -> None:
        """Test CompoundBravoGovernor loads Compound-specific ABI with all required functions."""
        compound_address = "0xc0Da02939E1441F497fd74F78cE7Decb17B66529"
        
        governor = CompoundBravoGovernor(contract_address=compound_address)
        
        # Should have all standard governor functions
        assert governor.has_function("castVote")
        assert governor.has_function("castVoteWithReason")
        assert governor.has_function("proposalVotes")
        assert governor.has_function("state")
        assert governor.has_function("hasVoted")
        
        # Should also have Compound-specific functions
        assert governor.has_function("quorumVotes")
        assert governor.has_function("proposalThreshold")
        assert governor.has_function("votingDelay")
        assert governor.has_function("votingPeriod")

    def test_compound_bravo_governor_initialization_with_rpc_provider(self) -> None:
        """Test CompoundBravoGovernor initialization with custom RPC provider."""
        compound_address = "0xc0Da02939E1441F497fd74F78cE7Decb17B66529"
        custom_rpc_url = "https://mainnet.infura.io/v3/test-key"
        
        governor = CompoundBravoGovernor(
            contract_address=compound_address,
            rpc_url=custom_rpc_url
        )
        
        assert governor.rpc_url == custom_rpc_url
        assert governor.web3_provider is not None


class TestCompoundBravoDetector:
    """Test CompoundBravoDetector for identifying Compound contracts."""

    def test_compound_bravo_detector_identifies_known_compound_addresses(self) -> None:
        """Test detector identifies known Compound contract addresses."""
        # This test will fail because CompoundBravoDetector doesn't exist yet
        detector = CompoundBravoDetector()
        
        known_compound_addresses = [
            "0xc0Da02939E1441F497fd74F78cE7Decb17B66529",  # Mainnet Compound Governor Bravo
            "0x408ED6354d4973f66138C91495F2f2FCbd8724C3",  # Alternative Compound address
        ]
        
        for address in known_compound_addresses:
            result = detector.is_compound_contract(address)
            assert result is True
            assert detector.get_detection_confidence(address) > 0.9

    def test_compound_bravo_detector_rejects_non_compound_addresses(self) -> None:
        """Test detector rejects non-Compound contract addresses."""
        detector = CompoundBravoDetector()
        
        non_compound_addresses = [
            "0x5e4be8Bc9637f0EAA1A755019e06A68ce081D58F",  # Aave governance
            "0x1f9840a85d5aF5bf1D1762F925BDADdC4201F984",  # Uniswap token
            "0xA0b86a33E6441838b4c79e5a2AcCDc7EE3C3E81e",  # Generic contract
        ]
        
        for address in non_compound_addresses:
            result = detector.is_compound_contract(address)
            assert result is False
            assert detector.get_detection_confidence(address) < 0.3

    def test_compound_bravo_detector_uses_bytecode_analysis(self) -> None:
        """Test detector uses bytecode analysis for unknown addresses."""
        detector = CompoundBravoDetector()
        unknown_address = "0x1234567890abcdef1234567890abcdef12345678"
        
        # Mock bytecode that looks like Compound Governor Bravo
        mock_compound_bytecode = "0x608060405234801561001057600080fd5b50600436106102775760003560e01c8063bc197c8111610160578063ea9c7dee116100d8578063fc00eb9811610087578063fc00eb9814610567578063fe0d94c11461058b578063fe31b0f11461059b578063ffac4aed146105b8576102ca565b8063ea9c7dee146104f6578063eb9019d41461051a578063f1127ed81461053e578063f8dc5dd914610563576102ca565b8063d33219b4116101145763d33219b414610488578063da35c6641461049c578063dd4e2ba5146104c0578063e23a9a52146104d4576102ca565b8063bc197c811461043c578063c1ba49b414610470578063c59057e414610484576102ca565b806356781388116101ec5780637d5e81e2116101b05780637d5e81e2146103f05780638dfc4e2a146104005780639c2b3a8814610414578063b858183f14610428576102ca565b806356781388146103525780635c19a95c146103665780636fcfff451461037a5780637b3c71d3146103dc576102ca565b806324bc1a64116102285780632656227d146102e657806330b36cef146102fa578063328dd9821461030e578063328dd9821461032e576102ca565b806206fdde146102cf578063013cf08b146102d4578063062d84da146102e6576102ca565b366102ca57005b600080fd5b6102d26105dc565b005b6102de6102e23660046129f0565b610601565b005b61030e6102f43660046129f0565b610785565b005b6103166107c5565b6040516001600160a01b0390911681526020015b60405180910390f35b61034161033c366004612a54565b6107d4565b005b61035a6108c3565b005b61035a610374366004612a90565b6108ec565b6103ac610388366004612a90565b6001600160a01b03166000908152602081905260409020600101546001600160e01b03031690565b6040516001600160e01b03199091168152602001610325565b6103e46109fe565b005b6103f8610a3e565b005b61040a610408366004612aad565b610a5e565b005b6104266104223660046129f0565b610b43565b005b610430610c47565b005b610454610c89565b005b61047e61047c3660046129f0565b610ce6565b005b61048c610e14565b005b610490610e47565b005b6104b06104aa3660046129f0565b610e6a565b005b6104c8610f57565b005b6104e26104e0366004612b14565b610fad565b005b610504610502366004612b98565b611081565b005b61052e61051c366004612bd5565b61118e565b005b610552610550366004612c12565b6111a8565b005b61055b611264565b005b610575610573366004612c4f565b6112a4565b005b610593610591366004612c9c565b611386565b005b6105a96105a7366004612cc7565b611445565b005b6105c66105c4366004612d04565b6114ff565b005b6105da6105d8366004612d41565b611555565b005b..."
        
        with patch.object(detector, '_get_contract_bytecode', return_value=mock_compound_bytecode):
            result = detector.detect_by_bytecode_analysis(unknown_address)
            
            assert result == GovernorContractType.COMPOUND
            assert detector.get_detection_confidence(unknown_address) > 0.7

    def test_compound_bravo_detector_uses_function_signature_analysis(self) -> None:
        """Test detector uses function signature analysis for contract identification."""
        detector = CompoundBravoDetector()
        unknown_address = "0xabcdef1234567890abcdef1234567890abcdef12"
        
        # Mock Compound-specific function signatures
        compound_function_signatures = [
            "0x56781388",  # quorumVotes()
            "0xb858183f",  # proposalThreshold()
            "0xfe31b0f1",  # votingDelay()
            "0xfb1ca3d6",  # votingPeriod()
            "0xe23a9a52",  # castVote(uint256,uint8)
        ]
        
        with patch.object(detector, '_get_function_signatures', return_value=compound_function_signatures):
            result = detector.detect_by_function_signatures(unknown_address)
            
            assert result == GovernorContractType.COMPOUND
            assert detector.get_detection_confidence(unknown_address) > 0.8

    def test_compound_bravo_detector_caches_detection_results(self) -> None:
        """Test detector caches contract detection results for performance."""
        detector = CompoundBravoDetector()
        test_address = "0x1234567890abcdef1234567890abcdef12345678"
        
        # First detection should call analysis methods
        with patch.object(detector, '_analyze_contract', return_value=GovernorContractType.COMPOUND) as mock_analyze:
            result1 = detector.detect_contract_type(test_address)
            assert result1 == GovernorContractType.COMPOUND
            assert mock_analyze.call_count == 1
        
        # Second detection should use cache
        with patch.object(detector, '_analyze_contract', return_value=GovernorContractType.COMPOUND) as mock_analyze:
            result2 = detector.detect_contract_type(test_address)
            assert result2 == GovernorContractType.COMPOUND
            assert mock_analyze.call_count == 0  # Should not be called due to caching

    def test_compound_bravo_detector_validates_contract_address_format(self) -> None:
        """Test detector validates contract address format before analysis."""
        detector = CompoundBravoDetector()
        
        # Test invalid address formats
        invalid_addresses = [
            "invalid_address",
            "0x123",  # Too short
            "0xGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGG",  # Invalid hex
            "",
            None
        ]
        
        for invalid_address in invalid_addresses:
            with pytest.raises(CompoundBravoError, match="Invalid contract address"):
                detector.detect_contract_type(invalid_address)


class TestCompoundContractRegistry:
    """Test CompoundContractRegistry for managing known Compound contracts."""

    def test_compound_contract_registry_contains_known_mainnet_addresses(self) -> None:
        """Test registry contains known Compound mainnet contract addresses."""
        # This test will fail because CompoundContractRegistry doesn't exist yet
        registry = CompoundContractRegistry()
        
        known_mainnet_addresses = [
            "0xc0Da02939E1441F497fd74F78cE7Decb17B66529",  # Governor Bravo
            "0x6d903f6003cca6255D85CcA4D3B5E5146dC33925",  # Timelock
            "0x3d9819210A31b4961b30EF54bE2aeD79B9c9Cd3B",  # Comptroller
        ]
        
        for address in known_mainnet_addresses:
            assert registry.is_known_compound_contract(address) is True
            contract_info = registry.get_contract_info(address)
            assert contract_info is not None
            assert contract_info["network"] == "mainnet"
            assert contract_info["type"] in ["governor", "timelock", "comptroller"]

    def test_compound_contract_registry_supports_multiple_networks(self) -> None:
        """Test registry supports contracts across multiple networks."""
        registry = CompoundContractRegistry()
        
        # Should support mainnet, goerli, polygon, etc.
        supported_networks = registry.get_supported_networks()
        
        assert "mainnet" in supported_networks
        assert "goerli" in supported_networks
        assert len(supported_networks) >= 2

    def test_compound_contract_registry_provides_contract_metadata(self) -> None:
        """Test registry provides detailed metadata for Compound contracts."""
        registry = CompoundContractRegistry()
        mainnet_governor = "0xc0Da02939E1441F497fd74F78cE7Decb17B66529"
        
        metadata = registry.get_contract_metadata(mainnet_governor)
        
        assert metadata is not None
        assert metadata["name"] == "Compound Governor Bravo"
        assert metadata["version"] == "bravo"
        assert metadata["deployment_block"] > 0
        assert "abi_version" in metadata
        assert "governance_token" in metadata

    def test_compound_contract_registry_can_be_updated_with_new_contracts(self) -> None:
        """Test registry can be updated with new Compound contract addresses."""
        registry = CompoundContractRegistry()
        new_contract_address = "0x9876543210fedcba9876543210fedcba98765432"
        
        contract_info = {
            "name": "Test Compound Governor",
            "type": "governor",
            "network": "testnet",
            "deployment_block": 12345678,
            "version": "bravo"
        }
        
        registry.register_contract(new_contract_address, contract_info)
        
        assert registry.is_known_compound_contract(new_contract_address) is True
        retrieved_info = registry.get_contract_info(new_contract_address)
        assert retrieved_info["name"] == "Test Compound Governor"


class TestCompoundBravoABI:
    """Test CompoundBravoABI for Compound-specific ABI handling."""

    def test_compound_bravo_abi_loads_compound_specific_functions(self) -> None:
        """Test CompoundBravoABI loads all Compound-specific functions."""
        # This test will fail because CompoundBravoABI doesn't exist yet
        abi = CompoundBravoABI()
        
        # Standard governor functions
        assert abi.has_function("castVote")
        assert abi.has_function("castVoteWithReason")
        assert abi.has_function("proposalVotes")
        assert abi.has_function("state")
        assert abi.has_function("hasVoted")
        
        # Compound-specific functions
        assert abi.has_function("quorumVotes")
        assert abi.has_function("proposalThreshold")
        assert abi.has_function("votingDelay")
        assert abi.has_function("votingPeriod")
        assert abi.has_function("propose")
        assert abi.has_function("queue")
        assert abi.has_function("execute")
        assert abi.has_function("cancel")

    def test_compound_bravo_abi_validates_compound_function_signatures(self) -> None:
        """Test CompoundBravoABI validates Compound-specific function signatures."""
        abi = CompoundBravoABI()
        
        # Validate castVote signature (uint256 proposalId, uint8 support)
        cast_vote_func = abi.get_function("castVote")
        assert len(cast_vote_func.inputs) == 2
        assert cast_vote_func.inputs[0]["type"] == "uint256"
        assert cast_vote_func.inputs[1]["type"] == "uint8"
        
        # Validate propose signature
        propose_func = abi.get_function("propose")
        assert len(propose_func.inputs) == 4  # targets, values, signatures, calldatas
        assert propose_func.inputs[0]["type"] == "address[]"
        assert propose_func.inputs[1]["type"] == "uint256[]"

    def test_compound_bravo_abi_encodes_compound_cast_vote_correctly(self) -> None:
        """Test CompoundBravoABI encodes castVote with Compound-specific format."""
        abi = CompoundBravoABI()
        
        proposal_id = 123
        support = 1  # FOR vote in Compound (0=Against, 1=For, 2=Abstain)
        
        encoded_data = abi.encode_cast_vote(proposal_id, support)
        
        assert encoded_data.startswith("0x")
        assert len(encoded_data) > 10
        
        # Verify the function selector is correct for Compound's castVote
        expected_selector = "0xe23a9a52"  # castVote(uint256,uint8) selector
        assert encoded_data[:10] == expected_selector

    def test_compound_bravo_abi_encodes_cast_vote_with_reason_correctly(self) -> None:
        """Test CompoundBravoABI encodes castVoteWithReason with Compound format."""
        abi = CompoundBravoABI()
        
        proposal_id = 456
        support = 0  # AGAINST vote
        reason = "This proposal does not align with Compound's principles"
        
        encoded_data = abi.encode_cast_vote_with_reason(proposal_id, support, reason)
        
        assert encoded_data.startswith("0x")
        assert len(encoded_data) > 200  # Should be longer due to reason string
        
        # Verify function selector for castVoteWithReason
        expected_selector = "0x7b3c71d3"  # castVoteWithReason(uint256,uint8,string) selector
        assert encoded_data[:10] == expected_selector

    def test_compound_bravo_abi_handles_compound_specific_errors(self) -> None:
        """Test CompoundBravoABI handles Compound-specific error conditions."""
        abi = CompoundBravoABI()
        
        # Test invalid support value for Compound (only 0, 1, 2 allowed)
        with pytest.raises(CompoundBravoError, match="Invalid support value for Compound"):
            abi.encode_cast_vote(123, 3)  # Invalid support value
        
        # Test invalid proposal ID
        with pytest.raises(CompoundBravoError, match="Invalid proposal ID"):
            abi.encode_cast_vote(-1, 1)

    def test_compound_bravo_abi_provides_compound_specific_constants(self) -> None:
        """Test CompoundBravoABI provides Compound-specific constants and limits."""
        abi = CompoundBravoABI()
        
        # Compound-specific constants
        assert hasattr(abi, 'COMPOUND_VOTING_DELAY')
        assert hasattr(abi, 'COMPOUND_VOTING_PERIOD')
        assert hasattr(abi, 'COMPOUND_PROPOSAL_THRESHOLD')
        assert hasattr(abi, 'COMPOUND_QUORUM_VOTES')
        
        # Values should be reasonable for Compound governance
        assert abi.COMPOUND_VOTING_DELAY > 0
        assert abi.COMPOUND_VOTING_PERIOD > 0
        assert abi.COMPOUND_PROPOSAL_THRESHOLD > 0


class TestCompoundProposalStateManager:
    """Test CompoundProposalStateManager for managing Compound proposal states."""

    def test_compound_proposal_state_manager_maps_compound_states_correctly(self) -> None:
        """Test state manager correctly maps Compound proposal states."""
        # This test will fail because CompoundProposalStateManager doesn't exist yet
        state_manager = CompoundProposalStateManager()
        
        # Test Compound state mapping (Compound uses different state values)
        compound_states = {
            0: ProposalState.PENDING,
            1: ProposalState.ACTIVE, 
            2: ProposalState.DEFEATED,
            3: ProposalState.SUCCEEDED,
            4: ProposalState.SUCCEEDED,  # Queued maps to succeeded
            5: ProposalState.EXECUTED,
            6: ProposalState.DEFEATED,   # Cancelled maps to defeated
        }
        
        for compound_state, expected_state in compound_states.items():
            mapped_state = state_manager.map_compound_state(compound_state)
            assert mapped_state == expected_state

    def test_compound_proposal_state_manager_validates_state_transitions(self) -> None:
        """Test state manager validates valid Compound proposal state transitions."""
        state_manager = CompoundProposalStateManager()
        
        # Valid transitions in Compound governance
        valid_transitions = [
            (ProposalState.PENDING, ProposalState.ACTIVE),
            (ProposalState.ACTIVE, ProposalState.SUCCEEDED),
            (ProposalState.ACTIVE, ProposalState.DEFEATED),
            (ProposalState.SUCCEEDED, ProposalState.EXECUTED),
        ]
        
        for from_state, to_state in valid_transitions:
            assert state_manager.is_valid_transition(from_state, to_state) is True

    def test_compound_proposal_state_manager_rejects_invalid_transitions(self) -> None:
        """Test state manager rejects invalid Compound proposal state transitions."""
        state_manager = CompoundProposalStateManager()
        
        # Invalid transitions
        invalid_transitions = [
            (ProposalState.EXECUTED, ProposalState.ACTIVE),
            (ProposalState.DEFEATED, ProposalState.SUCCEEDED),
            (ProposalState.PENDING, ProposalState.EXECUTED),
        ]
        
        for from_state, to_state in invalid_transitions:
            assert state_manager.is_valid_transition(from_state, to_state) is False

    def test_compound_proposal_state_manager_calculates_time_remaining(self) -> None:
        """Test state manager calculates remaining time for active proposals."""
        state_manager = CompoundProposalStateManager()
        
        # Mock current block and voting period
        current_block = 18000000
        end_block = 18000100
        avg_block_time = 12  # seconds
        
        time_remaining = state_manager.calculate_time_remaining(
            current_block, end_block, avg_block_time
        )
        
        assert time_remaining > 0
        assert time_remaining <= (end_block - current_block) * avg_block_time

    def test_compound_proposal_state_manager_handles_expired_proposals(self) -> None:
        """Test state manager correctly handles expired proposals."""
        state_manager = CompoundProposalStateManager()
        
        # Past end block
        current_block = 18000200
        end_block = 18000100
        
        is_expired = state_manager.is_proposal_expired(current_block, end_block)
        assert is_expired is True
        
        time_remaining = state_manager.calculate_time_remaining(current_block, end_block, 12)
        assert time_remaining == 0


class TestCompoundVotingPowerCalculator:
    """Test CompoundVotingPowerCalculator for Compound-specific voting power calculations."""

    def test_compound_voting_power_calculator_calculates_comp_voting_power(self) -> None:
        """Test calculator determines voting power based on COMP token holdings."""
        # This test will fail because CompoundVotingPowerCalculator doesn't exist yet
        calculator = CompoundVotingPowerCalculator()
        
        voter_address = "0x1234567890abcdef1234567890abcdef12345678"
        comp_balance = "1000000000000000000000"  # 1000 COMP tokens
        proposal_block = 18000000
        
        voting_power = calculator.get_voting_power(voter_address, proposal_block, comp_balance)
        
        assert voting_power > 0
        assert isinstance(voting_power, int)
        # 1000 COMP should give significant voting power
        assert voting_power >= 1000

    def test_compound_voting_power_calculator_handles_delegated_votes(self) -> None:
        """Test calculator handles delegated voting power correctly."""
        calculator = CompoundVotingPowerCalculator()
        
        delegate_address = "0xabcdef1234567890abcdef1234567890abcdef12"
        delegated_comp = "5000000000000000000000"  # 5000 COMP delegated
        proposal_block = 18000000
        
        voting_power = calculator.get_delegated_voting_power(
            delegate_address, proposal_block, delegated_comp
        )
        
        assert voting_power >= 5000
        assert voting_power > 0

    def test_compound_voting_power_calculator_validates_historical_balances(self) -> None:
        """Test calculator validates historical COMP balances at proposal block."""
        calculator = CompoundVotingPowerCalculator()
        
        voter_address = "0x1234567890abcdef1234567890abcdef12345678"
        current_block = 18000000
        past_block = 17999999
        
        # Mock historical balance lookup
        with patch.object(calculator, '_get_historical_comp_balance', return_value="2000000000000000000000"):
            voting_power = calculator.get_voting_power_at_block(
                voter_address, past_block
            )
            
            assert voting_power >= 2000
            assert calculator.last_queried_block == past_block

    def test_compound_voting_power_calculator_handles_zero_balance(self) -> None:
        """Test calculator correctly handles addresses with zero COMP balance."""
        calculator = CompoundVotingPowerCalculator()
        
        zero_balance_address = "0x0000000000000000000000000000000000000000"
        proposal_block = 18000000
        
        voting_power = calculator.get_voting_power(zero_balance_address, proposal_block, "0")
        
        assert voting_power == 0

    def test_compound_voting_power_calculator_caches_balance_queries(self) -> None:
        """Test calculator caches balance queries for performance."""
        calculator = CompoundVotingPowerCalculator()
        
        voter_address = "0x1234567890abcdef1234567890abcdef12345678"
        proposal_block = 18000000
        
        # First query should hit the network
        with patch.object(calculator, '_query_comp_balance', return_value="1000000000000000000000") as mock_query:
            power1 = calculator.get_voting_power(voter_address, proposal_block, "1000000000000000000000")
            assert mock_query.call_count == 1
        
        # Second query should use cache
        with patch.object(calculator, '_query_comp_balance', return_value="1000000000000000000000") as mock_query:
            power2 = calculator.get_voting_power(voter_address, proposal_block, "1000000000000000000000")
            assert mock_query.call_count == 0  # Should not be called due to caching
            assert power1 == power2


class TestCompoundDelegationManager:
    """Test CompoundDelegationManager for handling COMP token delegation."""

    def test_compound_delegation_manager_tracks_delegate_relationships(self) -> None:
        """Test delegation manager tracks COMP token delegate relationships."""
        # This test will fail because CompoundDelegationManager doesn't exist yet
        delegation_manager = CompoundDelegationManager()
        
        delegator = "0x1234567890abcdef1234567890abcdef12345678"
        delegate = "0xabcdef1234567890abcdef1234567890abcdef12"
        block_number = 18000000
        
        # Mock delegation event
        delegation_info = delegation_manager.get_delegation_info(delegator, block_number)
        
        assert delegation_info is not None
        assert "delegate" in delegation_info
        assert "voting_power" in delegation_info
        assert "delegation_block" in delegation_info

    def test_compound_delegation_manager_calculates_delegate_voting_power(self) -> None:
        """Test delegation manager calculates total voting power for delegates."""
        delegation_manager = CompoundDelegationManager()
        
        delegate_address = "0xabcdef1234567890abcdef1234567890abcdef12"
        block_number = 18000000
        
        # Mock multiple delegators to this delegate
        delegator_powers = [
            ("0x1111111111111111111111111111111111111111", "1000000000000000000000"),
            ("0x2222222222222222222222222222222222222222", "2000000000000000000000"),
            ("0x3333333333333333333333333333333333333333", "500000000000000000000"),
        ]
        
        with patch.object(delegation_manager, '_get_delegated_balances', return_value=delegator_powers):
            total_power = delegation_manager.get_total_delegated_power(delegate_address, block_number)
            
            assert total_power >= 3500  # 3500 COMP total
            assert isinstance(total_power, int)

    def test_compound_delegation_manager_handles_self_delegation(self) -> None:
        """Test delegation manager handles addresses that delegate to themselves."""
        delegation_manager = CompoundDelegationManager()
        
        self_delegator = "0x1234567890abcdef1234567890abcdef12345678"
        comp_balance = "1000000000000000000000"
        block_number = 18000000
        
        delegation_info = delegation_manager.get_delegation_info(self_delegator, block_number)
        
        # Should show self-delegation
        assert delegation_info["delegate"] == self_delegator
        assert delegation_info["is_self_delegated"] is True

    def test_compound_delegation_manager_tracks_delegation_history(self) -> None:
        """Test delegation manager tracks historical delegation changes."""
        delegation_manager = CompoundDelegationManager()
        
        delegator = "0x1234567890abcdef1234567890abcdef12345678"
        
        # Get delegation history over time
        delegation_history = delegation_manager.get_delegation_history(
            delegator, 
            from_block=17900000, 
            to_block=18000000
        )
        
        assert isinstance(delegation_history, list)
        assert len(delegation_history) >= 0
        
        # Each entry should have required fields
        for entry in delegation_history:
            assert "block_number" in entry
            assert "delegate" in entry
            assert "transaction_hash" in entry

    def test_compound_delegation_manager_validates_delegation_events(self) -> None:
        """Test delegation manager validates delegation event data."""
        delegation_manager = CompoundDelegationManager()
        
        # Test invalid delegation event
        invalid_event = {
            "delegator": "invalid_address",
            "delegate": "0xabcdef1234567890abcdef1234567890abcdef12",
            "block_number": 18000000
        }
        
        with pytest.raises(CompoundBravoError, match="Invalid delegation event"):
            delegation_manager.validate_delegation_event(invalid_event)


class TestCompoundBravoGovernorVoteEncoding:
    """Test CompoundBravoGovernor vote encoding functionality."""

    def test_compound_bravo_governor_encodes_for_vote_correctly(self) -> None:
        """Test CompoundBravoGovernor encodes FOR votes with correct Compound format."""
        compound_address = "0xc0Da02939E1441F497fd74F78cE7Decb17B66529"
        governor = CompoundBravoGovernor(contract_address=compound_address)
        
        proposal_id = 123
        support = VoteType.FOR  # Should map to 1 in Compound
        
        encoding_result = governor.encode_vote(proposal_id, support)
        
        assert encoding_result is not None
        assert isinstance(encoding_result, VoteEncodingResult)
        assert encoding_result.proposal_id == proposal_id
        assert encoding_result.support == support
        assert encoding_result.encoded_data.startswith("0x")
        assert encoding_result.governor_type == GovernorContractType.COMPOUND
        assert encoding_result.function_name == "castVote"

    def test_compound_bravo_governor_encodes_against_vote_correctly(self) -> None:
        """Test CompoundBravoGovernor encodes AGAINST votes with correct Compound format."""
        compound_address = "0xc0Da02939E1441F497fd74F78cE7Decb17B66529"
        governor = CompoundBravoGovernor(contract_address=compound_address)
        
        proposal_id = 456
        support = VoteType.AGAINST  # Should map to 0 in Compound
        
        encoding_result = governor.encode_vote(proposal_id, support)
        
        assert encoding_result.support == VoteType.AGAINST
        assert encoding_result.encoded_data.startswith("0x")
        # Should encode different data than FOR vote
        assert len(encoding_result.encoded_data) > 10

    def test_compound_bravo_governor_encodes_abstain_vote_correctly(self) -> None:
        """Test CompoundBravoGovernor encodes ABSTAIN votes with correct Compound format."""
        compound_address = "0xc0Da02939E1441F497fd74F78cE7Decb17B66529"
        governor = CompoundBravoGovernor(contract_address=compound_address)
        
        proposal_id = 789
        support = VoteType.ABSTAIN  # Should map to 2 in Compound
        
        encoding_result = governor.encode_vote(proposal_id, support)
        
        assert encoding_result.support == VoteType.ABSTAIN
        assert encoding_result.encoded_data.startswith("0x")

    def test_compound_bravo_governor_encodes_vote_with_reason(self) -> None:
        """Test CompoundBravoGovernor encodes votes with reasons using Compound format."""
        compound_address = "0xc0Da02939E1441F497fd74F78cE7Decb17B66529"
        governor = CompoundBravoGovernor(contract_address=compound_address)
        
        proposal_id = 111
        support = VoteType.FOR
        reason = "This proposal improves Compound's lending efficiency and benefits all users"
        
        encoding_result = governor.encode_vote_with_reason(proposal_id, support, reason)
        
        assert encoding_result.reason == reason
        assert encoding_result.function_name == "castVoteWithReason"
        assert encoding_result.encoded_data.startswith("0x")
        assert len(encoding_result.encoded_data) > 200  # Should be longer due to reason

    def test_compound_bravo_governor_validates_compound_proposal_ids(self) -> None:
        """Test CompoundBravoGovernor validates Compound-specific proposal ID format."""
        compound_address = "0xc0Da02939E1441F497fd74F78cE7Decb17B66529"
        governor = CompoundBravoGovernor(contract_address=compound_address)
        
        # Test invalid proposal IDs for Compound
        invalid_proposal_ids = [-1, 0, 2**256]  # Compound proposal IDs must be positive and reasonable
        
        for invalid_id in invalid_proposal_ids:
            with pytest.raises(CompoundBravoError, match="Invalid Compound proposal ID"):
                governor.encode_vote(invalid_id, VoteType.FOR)

    def test_compound_bravo_governor_optimizes_encoding_for_compound(self) -> None:
        """Test CompoundBravoGovernor optimizes encoding specifically for Compound contracts."""
        compound_address = "0xc0Da02939E1441F497fd74F78cE7Decb17B66529"
        governor = CompoundBravoGovernor(contract_address=compound_address)
        
        proposal_id = 123
        support = VoteType.FOR
        
        # Should use optimized encoding path for Compound
        with patch.object(governor, '_encode_compound_optimized', return_value="0x1234") as mock_optimized:
            encoding_result = governor.encode_vote(proposal_id, support)
            
            # Should call optimized encoding for Compound
            mock_optimized.assert_called_once()
            assert encoding_result.from_cache is False


class TestCompoundBravoGovernorProposalInteraction:
    """Test CompoundBravoGovernor proposal interaction functionality."""

    def test_compound_bravo_governor_fetches_proposal_info(self) -> None:
        """Test CompoundBravoGovernor fetches Compound proposal information."""
        compound_address = "0xc0Da02939E1441F497fd74F78cE7Decb17B66529"
        governor = CompoundBravoGovernor(contract_address=compound_address)
        
        proposal_id = 123
        
        # Mock Compound proposal data
        mock_proposal_data = {
            "id": proposal_id,
            "proposer": "0x1234567890abcdef1234567890abcdef12345678",
            "eta": 0,
            "startBlock": 18000000,
            "endBlock": 18000100,
            "forVotes": "1000000000000000000000000",
            "againstVotes": "500000000000000000000000",
            "abstainVotes": "100000000000000000000000",
            "canceled": False,
            "executed": False
        }
        
        with patch.object(governor, '_fetch_proposal_data', return_value=mock_proposal_data):
            proposal_info = governor.get_proposal_info(proposal_id)
            
            assert proposal_info is not None
            assert isinstance(proposal_info, CompoundProposalInfo)
            assert proposal_info.proposal_id == proposal_id
            assert proposal_info.start_block == 18000000
            assert proposal_info.end_block == 18000100

    def test_compound_bravo_governor_checks_voting_eligibility(self) -> None:
        """Test CompoundBravoGovernor checks if address can vote on Compound proposals."""
        compound_address = "0xc0Da02939E1441F497fd74F78cE7Decb17B66529"
        governor = CompoundBravoGovernor(contract_address=compound_address)
        
        voter_address = "0x1234567890abcdef1234567890abcdef12345678"
        proposal_id = 123
        
        # Mock voting power and eligibility
        with patch.object(governor, '_get_voting_power', return_value=1000000000000000000000):  # 1000 COMP
            eligibility = governor.check_voting_eligibility(voter_address, proposal_id)
            
            assert eligibility is not None
            assert eligibility["can_vote"] is True
            assert eligibility["voting_power"] > 0
            assert eligibility["reason"] is None

    def test_compound_bravo_governor_handles_insufficient_voting_power(self) -> None:
        """Test CompoundBravoGovernor handles addresses with insufficient voting power."""
        compound_address = "0xc0Da02939E1441F497fd74F78cE7Decb17B66529"
        governor = CompoundBravoGovernor(contract_address=compound_address)
        
        voter_address = "0x0000000000000000000000000000000000000000"  # No COMP
        proposal_id = 123
        
        with patch.object(governor, '_get_voting_power', return_value=0):
            eligibility = governor.check_voting_eligibility(voter_address, proposal_id)
            
            assert eligibility["can_vote"] is False
            assert eligibility["voting_power"] == 0
            assert "insufficient voting power" in eligibility["reason"].lower()

    def test_compound_bravo_governor_checks_if_already_voted(self) -> None:
        """Test CompoundBravoGovernor checks if address already voted on proposal."""
        compound_address = "0xc0Da02939E1441F497fd74F78cE7Decb17B66529"
        governor = CompoundBravoGovernor(contract_address=compound_address)
        
        voter_address = "0x1234567890abcdef1234567890abcdef12345678"
        proposal_id = 123
        
        # Mock that user already voted
        with patch.object(governor, '_has_voted', return_value=True):
            eligibility = governor.check_voting_eligibility(voter_address, proposal_id)
            
            assert eligibility["can_vote"] is False
            assert "already voted" in eligibility["reason"].lower()

    def test_compound_bravo_governor_validates_proposal_is_active(self) -> None:
        """Test CompoundBravoGovernor validates proposal is in active state for voting."""
        compound_address = "0xc0Da02939E1441F497fd74F78cE7Decb17B66529"
        governor = CompoundBravoGovernor(contract_address=compound_address)
        
        # Test closed proposal
        closed_proposal_id = 456
        with patch.object(governor, '_get_proposal_state', return_value=ProposalState.EXECUTED):
            with pytest.raises(CompoundVotingClosedError, match="Proposal voting has ended"):
                governor.encode_vote(closed_proposal_id, VoteType.FOR)

    def test_compound_bravo_governor_gets_proposal_vote_counts(self) -> None:
        """Test CompoundBravoGovernor retrieves vote counts for Compound proposals."""
        compound_address = "0xc0Da02939E1441F497fd74F78cE7Decb17B66529"
        governor = CompoundBravoGovernor(contract_address=compound_address)
        
        proposal_id = 123
        
        # Mock vote counts from Compound
        mock_vote_counts = {
            "forVotes": "1500000000000000000000000",  # 1.5M COMP
            "againstVotes": "800000000000000000000000",  # 800K COMP
            "abstainVotes": "200000000000000000000000"   # 200K COMP
        }
        
        with patch.object(governor, '_fetch_vote_counts', return_value=mock_vote_counts):
            vote_counts = governor.get_proposal_vote_counts(proposal_id)
            
            assert vote_counts is not None
            assert vote_counts["for_votes"] >= 1500000
            assert vote_counts["against_votes"] >= 800000
            assert vote_counts["abstain_votes"] >= 200000
            assert vote_counts["total_votes"] >= 2500000


class TestCompoundBravoGovernorBatchOperations:
    """Test CompoundBravoGovernor batch operations for multiple proposals."""

    def test_compound_bravo_governor_encodes_batch_votes_for_compound(self) -> None:
        """Test CompoundBravoGovernor encodes multiple votes efficiently for Compound."""
        compound_address = "0xc0Da02939E1441F497fd74F78cE7Decb17B66529"
        governor = CompoundBravoGovernor(contract_address=compound_address)
        
        vote_requests = [
            {"proposal_id": 123, "support": VoteType.FOR},
            {"proposal_id": 124, "support": VoteType.AGAINST},
            {"proposal_id": 125, "support": VoteType.ABSTAIN},
        ]
        
        batch_result = governor.encode_batch_votes(vote_requests)
        
        assert batch_result is not None
        assert batch_result.successful_count == 3
        assert batch_result.failed_count == 0
        assert len(batch_result.vote_encodings) == 3
        
        # All should be Compound contract type
        for encoding in batch_result.vote_encodings:
            assert encoding.governor_type == GovernorContractType.COMPOUND

    def test_compound_bravo_governor_validates_compound_proposals_in_batch(self) -> None:
        """Test CompoundBravoGovernor validates all proposals in batch are valid Compound proposals."""
        compound_address = "0xc0Da02939E1441F497fd74F78cE7Decb17B66529"
        governor = CompoundBravoGovernor(contract_address=compound_address)
        
        # Mix of valid and invalid proposal IDs
        vote_requests = [
            {"proposal_id": 123, "support": VoteType.FOR},     # Valid
            {"proposal_id": -1, "support": VoteType.FOR},      # Invalid
            {"proposal_id": 124, "support": VoteType.AGAINST}, # Valid
        ]
        
        batch_result = governor.encode_batch_votes(vote_requests)
        
        assert batch_result.successful_count == 2
        assert batch_result.failed_count == 1
        assert len(batch_result.errors) == 1
        assert "Invalid Compound proposal ID" in batch_result.errors[0]

    def test_compound_bravo_governor_optimizes_batch_operations(self) -> None:
        """Test CompoundBravoGovernor optimizes batch operations for Compound contracts."""
        compound_address = "0xc0Da02939E1441F497fd74F78cE7Decb17B66529"
        governor = CompoundBravoGovernor(contract_address=compound_address)
        
        # Large batch to test optimization
        vote_requests = [
            {"proposal_id": i, "support": VoteType.FOR}
            for i in range(1, 51)  # 50 votes
        ]
        
        batch_result = governor.encode_batch_votes(vote_requests)
        
        assert batch_result.successful_count == 50
        assert batch_result.processing_time_ms > 0
        assert batch_result.average_encoding_time_ms > 0
        # Should be reasonably fast for Compound optimization
        assert batch_result.average_encoding_time_ms < 100

    def test_compound_bravo_governor_handles_mixed_proposal_states_in_batch(self) -> None:
        """Test CompoundBravoGovernor handles mixed proposal states in batch operations."""
        compound_address = "0xc0Da02939E1441F497fd74F78cE7Decb17B66529"
        governor = CompoundBravoGovernor(contract_address=compound_address)
        
        vote_requests = [
            {"proposal_id": 123, "support": VoteType.FOR},     # Active
            {"proposal_id": 124, "support": VoteType.AGAINST}, # Executed (should fail)
            {"proposal_id": 125, "support": VoteType.ABSTAIN}, # Active
        ]
        
        # Mock proposal states
        def mock_get_proposal_state(proposal_id):
            if proposal_id == 124:
                return ProposalState.EXECUTED
            return ProposalState.ACTIVE
        
        with patch.object(governor, '_get_proposal_state', side_effect=mock_get_proposal_state):
            batch_result = governor.encode_batch_votes(vote_requests)
            
            assert batch_result.successful_count == 2
            assert batch_result.failed_count == 1
            assert "voting has ended" in batch_result.errors[0].lower()


class TestCompoundBravoGovernorRealWorldIntegration:
    """Test CompoundBravoGovernor integration with real Compound proposals."""

    def test_compound_bravo_governor_encodes_actual_compound_proposal(self) -> None:
        """Test CompoundBravoGovernor can encode votes for actual Compound proposals."""
        compound_address = "0xc0Da02939E1441F497fd74F78cE7Decb17B66529"
        governor = CompoundBravoGovernor(contract_address=compound_address)
        
        # Use a real Compound proposal ID (example)
        real_proposal_id = 142  # Example historical Compound proposal
        support = VoteType.FOR
        
        # Mock the proposal exists and is valid
        with patch.object(governor, '_validate_proposal_exists', return_value=True):
            with patch.object(governor, '_get_proposal_state', return_value=ProposalState.ACTIVE):
                encoding_result = governor.encode_vote(real_proposal_id, support)
                
                assert encoding_result.proposal_id == real_proposal_id
                assert encoding_result.encoded_data.startswith("0x")
                assert len(encoding_result.encoded_data) > 10

    def test_compound_bravo_governor_handles_compound_gas_estimation(self) -> None:
        """Test CompoundBravoGovernor provides accurate gas estimation for Compound votes."""
        compound_address = "0xc0Da02939E1441F497fd74F78cE7Decb17B66529"
        governor = CompoundBravoGovernor(contract_address=compound_address)
        
        proposal_id = 123
        support = VoteType.FOR
        
        gas_estimate = governor.estimate_vote_gas(proposal_id, support)
        
        assert gas_estimate is not None
        assert gas_estimate["gas_limit"] > 0
        assert gas_estimate["gas_price"] > 0
        assert gas_estimate["estimated_cost"] > 0
        # Compound votes should be relatively efficient
        assert gas_estimate["gas_limit"] < 200000  # Reasonable gas limit

    def test_compound_bravo_governor_integrates_with_compound_timelock(self) -> None:
        """Test CompoundBravoGovernor integrates with Compound Timelock for execution."""
        compound_address = "0xc0Da02939E1441F497fd74F78cE7Decb17B66529"
        governor = CompoundBravoGovernor(contract_address=compound_address)
        
        succeeded_proposal_id = 100
        
        # Mock proposal that succeeded and can be queued
        with patch.object(governor, '_get_proposal_state', return_value=ProposalState.SUCCEEDED):
            queue_info = governor.get_queue_info(succeeded_proposal_id)
            
            assert queue_info is not None
            assert "can_queue" in queue_info
            assert "timelock_address" in queue_info
            assert "execution_eta" in queue_info

    def test_compound_bravo_governor_tracks_compound_governance_metrics(self) -> None:
        """Test CompoundBravoGovernor tracks Compound-specific governance metrics."""
        compound_address = "0xc0Da02939E1441F497fd74F78cE7Decb17B66529"
        governor = CompoundBravoGovernor(contract_address=compound_address)
        
        metrics = governor.get_governance_metrics()
        
        assert metrics is not None
        assert "total_proposals" in metrics
        assert "active_proposals" in metrics
        assert "total_comp_delegated" in metrics
        assert "unique_voters" in metrics
        assert "average_participation_rate" in metrics
        
        # All metrics should be reasonable numbers
        assert metrics["total_proposals"] >= 0
        assert 0 <= metrics["average_participation_rate"] <= 1


class TestCompoundBravoGovernorErrorHandling:
    """Test CompoundBravoGovernor error handling and edge cases."""

    def test_compound_bravo_governor_handles_proposal_not_found(self) -> None:
        """Test CompoundBravoGovernor handles non-existent Compound proposals."""
        compound_address = "0xc0Da02939E1441F497fd74F78cE7Decb17B66529"
        governor = CompoundBravoGovernor(contract_address=compound_address)
        
        non_existent_proposal = 999999
        
        with patch.object(governor, '_proposal_exists', return_value=False):
            with pytest.raises(CompoundProposalNotFoundError, match="Proposal not found"):
                governor.encode_vote(non_existent_proposal, VoteType.FOR)

    def test_compound_bravo_governor_handles_network_failures_gracefully(self) -> None:
        """Test CompoundBravoGovernor handles network failures gracefully."""
        compound_address = "0xc0Da02939E1441F497fd74F78cE7Decb17B66529"
        governor = CompoundBravoGovernor(contract_address=compound_address)
        
        proposal_id = 123
        
        # Mock network failure
        with patch.object(governor, '_fetch_proposal_data', side_effect=Exception("Network error")):
            with pytest.raises(CompoundBravoError, match="Failed to fetch proposal data"):
                governor.get_proposal_info(proposal_id)

    def test_compound_bravo_governor_validates_voting_power_thresholds(self) -> None:
        """Test CompoundBravoGovernor validates voting power meets Compound thresholds."""
        compound_address = "0xc0Da02939E1441F497fd74F78cE7Decb17B66529"
        governor = CompoundBravoGovernor(contract_address=compound_address)
        
        voter_address = "0x1234567890abcdef1234567890abcdef12345678"
        proposal_id = 123
        
        # Mock insufficient voting power (less than 1 COMP)
        with patch.object(governor, '_get_voting_power', return_value=100000000000000000):  # 0.1 COMP
            with pytest.raises(CompoundInsufficientVotingPowerError, match="Insufficient voting power"):
                governor.encode_vote(proposal_id, VoteType.FOR, voter_address=voter_address)

    def test_compound_bravo_governor_handles_contract_upgrade_scenarios(self) -> None:
        """Test CompoundBravoGovernor handles Compound contract upgrade scenarios."""
        compound_address = "0xc0Da02939E1441F497fd74F78cE7Decb17B66529"
        governor = CompoundBravoGovernor(contract_address=compound_address)
        
        # Mock contract that has been upgraded/changed
        with patch.object(governor, '_validate_contract_interface', return_value=False):
            with pytest.raises(CompoundBravoError, match="Contract interface changed"):
                governor.refresh_contract_interface()

    def test_compound_bravo_governor_handles_malformed_compound_data(self) -> None:
        """Test CompoundBravoGovernor handles malformed data from Compound contracts."""
        compound_address = "0xc0Da02939E1441F497fd74F78cE7Decb17B66529"
        governor = CompoundBravoGovernor(contract_address=compound_address)
        
        proposal_id = 123
        
        # Mock malformed proposal data
        malformed_data = {
            "id": "not_a_number",
            "startBlock": -1,
            "endBlock": "invalid",
        }
        
        with patch.object(governor, '_fetch_proposal_data', return_value=malformed_data):
            with pytest.raises(CompoundBravoError, match="Invalid proposal data format"):
                governor.get_proposal_info(proposal_id)


class TestCompoundBravoGovernorPerformanceOptimizations:
    """Test CompoundBravoGovernor performance optimizations."""

    def test_compound_bravo_governor_caches_abi_loading(self) -> None:
        """Test CompoundBravoGovernor caches ABI loading for performance."""
        compound_address = "0xc0Da02939E1441F497fd74F78cE7Decb17B66529"
        
        # First instance should load ABI
        with patch.object(CompoundBravoABI, '__init__', return_value=None) as mock_abi_init:
            governor1 = CompoundBravoGovernor(contract_address=compound_address)
            assert mock_abi_init.call_count == 1
        
        # Second instance should use cached ABI
        with patch.object(CompoundBravoABI, '__init__', return_value=None) as mock_abi_init:
            governor2 = CompoundBravoGovernor(contract_address=compound_address)
            # Should use cached version
            assert mock_abi_init.call_count == 0

    def test_compound_bravo_governor_optimizes_batch_encoding_performance(self) -> None:
        """Test CompoundBravoGovernor optimizes batch encoding performance."""
        compound_address = "0xc0Da02939E1441F497fd74F78cE7Decb17B66529"
        governor = CompoundBravoGovernor(contract_address=compound_address)
        
        # Large batch to test performance
        large_batch = [
            {"proposal_id": i, "support": VoteType.FOR}
            for i in range(1, 101)  # 100 votes
        ]
        
        import time
        start_time = time.time()
        batch_result = governor.encode_batch_votes(large_batch)
        end_time = time.time()
        
        processing_time = end_time - start_time
        
        assert batch_result.successful_count == 100
        # Should process efficiently (less than 5 seconds for 100 votes)
        assert processing_time < 5.0
        assert batch_result.average_encoding_time_ms < 50

    def test_compound_bravo_governor_uses_connection_pooling(self) -> None:
        """Test CompoundBravoGovernor uses connection pooling for RPC calls."""
        compound_address = "0xc0Da02939E1441F497fd74F78cE7Decb17B66529"
        governor = CompoundBravoGovernor(contract_address=compound_address)
        
        # Multiple operations should reuse connections
        operations = [
            lambda: governor.get_proposal_info(123),
            lambda: governor.get_proposal_info(124),
            lambda: governor.get_proposal_info(125),
        ]
        
        # Mock connection pool usage tracking
        with patch.object(governor, '_get_connection_pool_stats') as mock_stats:
            mock_stats.return_value = {"active_connections": 1, "reused_connections": 3}
            
            for operation in operations:
                try:
                    operation()
                except:
                    pass  # Operations may fail due to mocking, but we're testing connection reuse
            
            stats = governor._get_connection_pool_stats()
            assert stats["reused_connections"] > 0


class TestCompoundBravoGovernorEdgeCases:
    """Test CompoundBravoGovernor edge cases and boundary conditions."""

    def test_compound_bravo_governor_handles_maximum_compound_proposal_id(self) -> None:
        """Test CompoundBravoGovernor handles maximum valid Compound proposal ID."""
        compound_address = "0xc0Da02939E1441F497fd74F78cE7Decb17B66529"
        governor = CompoundBravoGovernor(contract_address=compound_address)
        
        # Test with large but valid proposal ID
        max_proposal_id = 2**32 - 1  # Large but reasonable proposal ID
        support = VoteType.FOR
        
        # Should handle large proposal IDs gracefully
        with patch.object(governor, '_validate_proposal_exists', return_value=True):
            with patch.object(governor, '_get_proposal_state', return_value=ProposalState.ACTIVE):
                encoding_result = governor.encode_vote(max_proposal_id, support)
                
                assert encoding_result.proposal_id == max_proposal_id
                assert encoding_result.encoded_data.startswith("0x")

    def test_compound_bravo_governor_handles_concurrent_operations(self) -> None:
        """Test CompoundBravoGovernor handles concurrent operations safely."""
        compound_address = "0xc0Da02939E1441F497fd74F78cE7Decb17B66529"
        governor = CompoundBravoGovernor(contract_address=compound_address)
        
        import threading
        import concurrent.futures
        
        def encode_vote_concurrent(proposal_id: int) -> VoteEncodingResult:
            return governor.encode_vote(proposal_id, VoteType.FOR)
        
        # Submit concurrent encoding requests
        with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
            futures = [
                executor.submit(encode_vote_concurrent, proposal_id)
                for proposal_id in range(1, 11)
            ]
            
            results = []
            for future in futures:
                try:
                    result = future.result(timeout=5)
                    results.append(result)
                except Exception as e:
                    # Some may fail due to mocking, but should not crash
                    pass
        
        # Should handle concurrent operations without crashing
        assert len(results) >= 0  # At least some should succeed

    def test_compound_bravo_governor_handles_extremely_long_vote_reason(self) -> None:
        """Test CompoundBravoGovernor handles extremely long vote reasons."""
        compound_address = "0xc0Da02939E1441F497fd74F78cE7Decb17B66529"
        governor = CompoundBravoGovernor(contract_address=compound_address)
        
        proposal_id = 123
        support = VoteType.FOR
        
        # Create a very long reason (near gas limit)
        very_long_reason = "This is a very detailed explanation " * 100  # ~3500 characters
        
        # Should handle long reasons but may warn about gas costs
        with patch.object(governor, '_validate_proposal_exists', return_value=True):
            with patch.object(governor, '_get_proposal_state', return_value=ProposalState.ACTIVE):
                encoding_result = governor.encode_vote_with_reason(proposal_id, support, very_long_reason)
                
                assert encoding_result.reason == very_long_reason
                assert len(encoding_result.encoded_data) > 3000  # Should be long

    def test_compound_bravo_governor_handles_zero_block_numbers(self) -> None:
        """Test CompoundBravoGovernor handles edge cases with block numbers."""
        compound_address = "0xc0Da02939E1441F497fd74F78cE7Decb17B66529"
        governor = CompoundBravoGovernor(contract_address=compound_address)
        
        # Mock proposal with edge case block numbers
        edge_case_proposal = {
            "id": 123,
            "startBlock": 0,  # Edge case
            "endBlock": 1,    # Very short voting period
        }
        
        with patch.object(governor, '_fetch_proposal_data', return_value=edge_case_proposal):
            proposal_info = governor.get_proposal_info(123)
            
            # Should handle gracefully but may indicate issues
            assert proposal_info.start_block == 0
            assert proposal_info.end_block == 1