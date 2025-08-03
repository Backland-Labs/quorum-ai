"""Tests for VotingService."""

import pytest
from unittest.mock import patch, MagicMock, mock_open, call
import time
import requests
from pytest_httpx import HTTPXMock

from services.voting_service import VotingService


class TestVotingServiceInitialization:
    """Test VotingService initialization."""

    @patch("builtins.open", new_callable=mock_open, read_data="0x1234567890abcdef1234567890abcdef1234567890abcdef1234567890abcdef")
    def test_voting_service_initialization(self, mock_file):
        """Test VotingService initialization loads account correctly."""
        service = VotingService()
        
        assert service.account.address is not None
        # Check that ethereum_private_key.txt was opened
        private_key_calls = [call for call in mock_file.call_args_list if call[0][0] == "ethereum_private_key.txt"]
        assert len(private_key_calls) == 1
        assert private_key_calls[0][0] == ("ethereum_private_key.txt", "r")


class TestVotingServiceSnapshotMessageCreation:
    """Test VotingService Snapshot message creation."""
    
    @patch("builtins.open", new_callable=mock_open, read_data="0x1234567890abcdef1234567890abcdef1234567890abcdef1234567890abcdef")
    def test_create_snapshot_vote_message_basic(self, mock_file):
        """Test basic Snapshot vote message creation."""
        service = VotingService()
        
        space = "aave.eth"
        proposal = "0xabcdef123456789"
        choice = 1
        timestamp = 1640995200  # Fixed timestamp for testing
        
        message = service.create_snapshot_vote_message(space, proposal, choice, timestamp)
        
        assert message["domain"]["name"] == "snapshot"
        assert message["domain"]["version"] == "0.1.4"
        assert message["primaryType"] == "Vote"
        assert message["message"]["space"] == space
        assert message["message"]["proposal"] == proposal
        assert message["message"]["choice"] == choice
        assert message["message"]["timestamp"] == timestamp
        assert message["message"]["from"] == service.account.address
        assert message["message"]["reason"] == ""
        assert message["message"]["app"] == ""
        assert message["message"]["metadata"] == "{}"
        
    @patch("builtins.open", new_callable=mock_open, read_data="0x1234567890abcdef1234567890abcdef1234567890abcdef1234567890abcdef")
    @patch("time.time")
    def test_create_snapshot_vote_message_default_timestamp(self, mock_time, mock_file):
        """Test Snapshot vote message creation with default timestamp."""
        mock_time.return_value = 1640995200.5
        service = VotingService()
        
        message = service.create_snapshot_vote_message("test.eth", "proposal123", 2)
        
        assert message["message"]["timestamp"] == 1640995200  # Should be int
        
    @patch("builtins.open", new_callable=mock_open, read_data="0x1234567890abcdef1234567890abcdef1234567890abcdef1234567890abcdef")
    def test_create_snapshot_vote_message_bytes32_proposal(self, mock_file):
        """Test Snapshot vote message with bytes32 proposal format."""
        service = VotingService()
        
        # 66 character hex string (0x + 64 hex chars = 32 bytes)
        bytes32_proposal = "0x" + "a" * 64
        
        message = service.create_snapshot_vote_message("test.eth", bytes32_proposal, 1)
        
        # Check that proposal type is bytes32 for 66-char hex strings
        vote_type = None
        for field in message["types"]["Vote"]:
            if field["name"] == "proposal":
                vote_type = field["type"]
                break
        
        assert vote_type == "bytes32"
        
    @patch("builtins.open", new_callable=mock_open, read_data="0x1234567890abcdef1234567890abcdef1234567890abcdef1234567890abcdef")
    def test_create_snapshot_vote_message_string_proposal(self, mock_file):
        """Test Snapshot vote message with string proposal format."""
        service = VotingService()
        
        string_proposal = "QmSomeIPFSHash"
        
        message = service.create_snapshot_vote_message("test.eth", string_proposal, 1)
        
        # Check that proposal type is string for non-bytes32 format
        vote_type = None
        for field in message["types"]["Vote"]:
            if field["name"] == "proposal":
                vote_type = field["type"]
                break
        
        assert vote_type == "string"


class TestVotingServiceMessageSigning:
    """Test VotingService message signing functionality."""
    
    @patch("builtins.open", new_callable=mock_open, read_data="0x1234567890abcdef1234567890abcdef1234567890abcdef1234567890abcdef")
    def test_sign_snapshot_message(self, mock_file):
        """Test signing a Snapshot vote message."""
        service = VotingService()
        
        # Create a test message
        message = service.create_snapshot_vote_message("test.eth", "proposal123", 1, 1640995200)
        
        # Sign the message
        signature = service.sign_snapshot_message(message)
        
        # Should return a hex string signature
        assert isinstance(signature, str)
        assert signature.startswith("0x")
        assert len(signature) == 132  # 0x + 130 hex chars (65 bytes * 2)
        
    @patch("builtins.open", new_callable=mock_open, read_data="0x1234567890abcdef1234567890abcdef1234567890abcdef1234567890abcdef")
    def test_sign_snapshot_message_deterministic(self, mock_file):
        """Test that signing the same message produces the same signature."""
        service = VotingService()
        
        message = service.create_snapshot_vote_message("test.eth", "proposal123", 1, 1640995200)
        
        sig1 = service.sign_snapshot_message(message)
        sig2 = service.sign_snapshot_message(message)
        
        assert sig1 == sig2


class TestVotingServiceSnapshotSubmission:
    """Test VotingService Snapshot vote submission."""
    
    @patch("builtins.open", new_callable=mock_open, read_data="0x1234567890abcdef1234567890abcdef1234567890abcdef1234567890abcdef")
    @pytest.mark.asyncio
    async def test_submit_vote_to_snapshot_success(self, mock_file, httpx_mock: HTTPXMock):
        """Test successful vote submission to Snapshot."""
        # Mock successful Snapshot API response
        httpx_mock.add_response(
            method="POST",
            url="https://seq.snapshot.org/",
            json={"id": "vote_123", "ipfs": "QmHash"},
            status_code=200
        )
        
        service = VotingService()
        
        message = service.create_snapshot_vote_message("test.eth", "proposal123", 1, 1640995200)
        signature = service.sign_snapshot_message(message)
        
        result = await service.submit_vote_to_snapshot(message, signature)
        
        assert result["success"] is True
        assert "response" in result
        assert result["response"]["id"] == "vote_123"
        
    @patch("builtins.open", new_callable=mock_open, read_data="0x1234567890abcdef1234567890abcdef1234567890abcdef1234567890abcdef")
    @pytest.mark.asyncio
    async def test_submit_vote_to_snapshot_failure(self, mock_file, httpx_mock: HTTPXMock):
        """Test failed vote submission to Snapshot."""
        # Mock failed Snapshot API response
        httpx_mock.add_response(
            method="POST",
            url="https://seq.snapshot.org/",
            status_code=400,
            text="Invalid signature"
        )
        
        service = VotingService()
        
        message = service.create_snapshot_vote_message("test.eth", "proposal123", 1, 1640995200)
        signature = service.sign_snapshot_message(message)
        
        result = await service.submit_vote_to_snapshot(message, signature)
        
        assert result["success"] is False
        assert "error" in result
        assert "Invalid signature" in result.get("response_text", "")
        
    @patch("builtins.open", new_callable=mock_open, read_data="0x1234567890abcdef1234567890abcdef1234567890abcdef1234567890abcdef")
    @pytest.mark.asyncio
    async def test_submit_vote_to_snapshot_network_error(self, mock_file):
        """Test vote submission with network error."""
        service = VotingService()
        
        message = service.create_snapshot_vote_message("test.eth", "proposal123", 1, 1640995200)
        signature = service.sign_snapshot_message(message)
        
        # Mock network error
        with patch("httpx.AsyncClient.post", side_effect=requests.exceptions.ConnectionError("Network error")):
            result = await service.submit_vote_to_snapshot(message, signature)
            
            assert result["success"] is False
            assert "Network error" in result["error"]


class TestVotingServiceSignatureFormatting:
    """Test VotingService signature formatting."""
    
    @patch("builtins.open", new_callable=mock_open, read_data="0x1234567890abcdef1234567890abcdef1234567890abcdef1234567890abcdef")
    @pytest.mark.asyncio
    async def test_submit_vote_signature_with_0x_prefix(self, mock_file, httpx_mock: HTTPXMock):
        """Test vote submission with signature that already has 0x prefix."""
        httpx_mock.add_response(
            method="POST",
            url="https://seq.snapshot.org/",
            json={"id": "vote_123"},
            status_code=200
        )
        
        service = VotingService()
        
        message = service.create_snapshot_vote_message("test.eth", "proposal123", 1)
        signature = "0xabcdef123456"  # Already has 0x prefix
        
        await service.submit_vote_to_snapshot(message, signature)
        
        # Check the request was made with proper formatting
        request = httpx_mock.get_requests()[0]
        request_data = request.read()
        import json
        request_json = json.loads(request_data.decode())
        
        # The signature should maintain the 0x prefix
        assert request_json["sig"] == "0xabcdef123456"
        
    @patch("builtins.open", new_callable=mock_open, read_data="0x1234567890abcdef1234567890abcdef1234567890abcdef1234567890abcdef")
    @pytest.mark.asyncio
    async def test_submit_vote_signature_without_0x_prefix(self, mock_file, httpx_mock: HTTPXMock):
        """Test vote submission with signature without 0x prefix."""
        httpx_mock.add_response(
            method="POST",
            url="https://seq.snapshot.org/",
            json={"id": "vote_123"},
            status_code=200
        )
        
        service = VotingService()
        
        message = service.create_snapshot_vote_message("test.eth", "proposal123", 1)
        signature = "abcdef123456"  # No 0x prefix
        
        await service.submit_vote_to_snapshot(message, signature)
        
        # Check the request was made with proper formatting
        request = httpx_mock.get_requests()[0]
        request_data = request.read()
        import json
        request_json = json.loads(request_data.decode())
        
        # The signature should have 0x prefix added
        assert request_json["sig"] == "0xabcdef123456"


class TestVotingServiceCompleteWorkflow:
    """Test VotingService complete voting workflow."""
    
    @patch("builtins.open", new_callable=mock_open, read_data="0x1234567890abcdef1234567890abcdef1234567890abcdef1234567890abcdef")
    @pytest.mark.asyncio
    async def test_vote_on_proposal_success(self, mock_file, httpx_mock: HTTPXMock):
        """Test complete voting workflow success."""
        httpx_mock.add_response(
            method="POST",
            url="https://seq.snapshot.org/",
            json={"id": "vote_123", "ipfs": "QmHash"},
            status_code=200
        )
        
        service = VotingService()
        
        result = await service.vote_on_proposal(
            space="aave.eth",
            proposal="proposal123",
            choice=1
        )
        
        assert result["success"] is True
        assert "vote_message" in result
        assert "signature" in result
        assert "submission_result" in result
        assert result["submission_result"]["success"] is True
        
    @patch("builtins.open", new_callable=mock_open, read_data="0x1234567890abcdef1234567890abcdef1234567890abcdef1234567890abcdef")
    @pytest.mark.asyncio
    async def test_vote_on_proposal_submission_failure(self, mock_file, httpx_mock: HTTPXMock):
        """Test complete voting workflow with submission failure."""
        httpx_mock.add_response(
            method="POST",
            url="https://seq.snapshot.org/",
            status_code=400,
            text="Invalid vote"
        )
        
        service = VotingService()
        
        result = await service.vote_on_proposal(
            space="aave.eth",
            proposal="proposal123", 
            choice=1
        )
        
        assert result["success"] is False
        assert "vote_message" in result  # Message still created
        assert "signature" in result     # Signature still created
        assert "submission_result" in result
        assert result["submission_result"]["success"] is False
        
    @patch("builtins.open", new_callable=mock_open, read_data="0x1234567890abcdef1234567890abcdef1234567890abcdef1234567890abcdef")
    @pytest.mark.asyncio
    async def test_vote_on_proposal_with_custom_timestamp(self, mock_file, httpx_mock: HTTPXMock):
        """Test voting workflow with custom timestamp."""
        httpx_mock.add_response(
            method="POST",
            url="https://seq.snapshot.org/",
            json={"id": "vote_123"},
            status_code=200
        )
        
        service = VotingService()
        custom_timestamp = 1640995200
        
        result = await service.vote_on_proposal(
            space="test.eth",
            proposal="proposal123",
            choice=2,
            timestamp=custom_timestamp
        )
        
        assert result["success"] is True
        assert result["vote_message"]["message"]["timestamp"] == custom_timestamp