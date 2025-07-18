import pytest
from backend.utils.vote_encoder import (
    Support,
    encode_cast_vote,
    VoteEncoderError,
    validate_proposal_id,
    validate_reason_length
)
from backend.services.governor_registry import GovernorType


class TestSupport:
    def test_support_enum_values(self):
        assert Support.AGAINST == 0
        assert Support.FOR == 1
        assert Support.ABSTAIN == 2

    def test_support_int_conversion(self):
        assert int(Support.AGAINST) == 0
        assert int(Support.FOR) == 1
        assert int(Support.ABSTAIN) == 2


class TestValidation:
    def test_validate_proposal_id_valid(self):
        assert validate_proposal_id(1) == 1
        assert validate_proposal_id(999999) == 999999

    def test_validate_proposal_id_invalid(self):
        with pytest.raises(VoteEncoderError, match="Proposal ID must be non-negative"):
            validate_proposal_id(-1)

    def test_validate_reason_length_valid(self):
        assert validate_reason_length("Valid reason") == "Valid reason"
        assert validate_reason_length("") == ""
        assert validate_reason_length(None) is None

    def test_validate_reason_length_too_long(self):
        long_reason = "x" * 257
        with pytest.raises(VoteEncoderError, match="Reason too long"):
            validate_reason_length(long_reason)


class TestVoteEncoding:
    def test_encode_cast_vote_without_reason(self):
        encoded = encode_cast_vote(
            governor_id="compound-mainnet",
            proposal_id=123,
            support=Support.FOR
        )
        
        assert isinstance(encoded, str)
        assert encoded.startswith("0x")
        assert len(encoded) > 10

    def test_encode_cast_vote_with_reason(self):
        encoded = encode_cast_vote(
            governor_id="compound-mainnet", 
            proposal_id=123,
            support=Support.FOR,
            reason="I support this proposal"
        )
        
        assert isinstance(encoded, str)
        assert encoded.startswith("0x")
        assert len(encoded) > 10

    def test_encode_cast_vote_all_support_types(self):
        for support in [Support.AGAINST, Support.FOR, Support.ABSTAIN]:
            encoded = encode_cast_vote(
                governor_id="compound-mainnet",
                proposal_id=123,
                support=support
            )
            
            assert isinstance(encoded, str)
            assert encoded.startswith("0x")

    def test_encode_cast_vote_all_governor_types(self):
        governor_ids = [
            "compound-mainnet",
            "nouns-mainnet", 
            "uniswap-mainnet",
            "arbitrum-mainnet"
        ]
        
        for gov_id in governor_ids:
            encoded = encode_cast_vote(
                governor_id=gov_id,
                proposal_id=123,
                support=Support.FOR
            )
            
            assert isinstance(encoded, str)
            assert encoded.startswith("0x")

    def test_encode_cast_vote_invalid_governor(self):
        with pytest.raises(VoteEncoderError, match="Governor 'invalid' not found"):
            encode_cast_vote(
                governor_id="invalid",
                proposal_id=123,
                support=Support.FOR
            )

    def test_encode_cast_vote_invalid_proposal_id(self):
        with pytest.raises(VoteEncoderError, match="Proposal ID must be non-negative"):
            encode_cast_vote(
                governor_id="compound-mainnet",
                proposal_id=-1,
                support=Support.FOR
            )

    def test_encode_cast_vote_reason_too_long(self):
        long_reason = "x" * 257
        
        with pytest.raises(VoteEncoderError, match="Reason too long"):
            encode_cast_vote(
                governor_id="compound-mainnet",
                proposal_id=123,
                support=Support.FOR,
                reason=long_reason
            )

    def test_encoded_data_differs_with_without_reason(self):
        encoded_without = encode_cast_vote(
            governor_id="compound-mainnet",
            proposal_id=123,
            support=Support.FOR
        )
        
        encoded_with = encode_cast_vote(
            governor_id="compound-mainnet",
            proposal_id=123,
            support=Support.FOR,
            reason="Test reason"
        )
        
        assert encoded_without != encoded_with

    def test_encoded_data_differs_by_support_value(self):
        encoded_for = encode_cast_vote(
            governor_id="compound-mainnet",
            proposal_id=123,
            support=Support.FOR
        )
        
        encoded_against = encode_cast_vote(
            governor_id="compound-mainnet",
            proposal_id=123,
            support=Support.AGAINST
        )
        
        assert encoded_for != encoded_against
