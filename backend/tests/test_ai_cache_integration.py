"""Integration tests for AI service caching functionality."""

import pytest
from unittest.mock import patch, MagicMock, AsyncMock
import asyncio

from services.ai_service import AIService
from services.cache_service import CacheService
from models import Proposal, ProposalSummary


class TestAICacheIntegration:
    """Integration tests for AI service caching with Redis backend."""

    @pytest.mark.asyncio
    async def test_end_to_end_caching_flow(
        self, sample_proposal: Proposal, complex_proposal: Proposal
    ) -> None:
        """Test complete end-to-end caching flow with real cache service."""
        # Arrange - Mock Redis operations but keep cache service logic
        mock_redis_client = AsyncMock()
        mock_pool = MagicMock()
        
        # Mock Redis operations for caching
        mock_redis_client.get = AsyncMock(return_value=None)  # Cache miss first
        mock_redis_client.setex = AsyncMock(return_value=True)
        mock_redis_client.set = AsyncMock(return_value=True)  # For locks
        mock_redis_client.delete = AsyncMock(return_value=1)
        mock_redis_client.exists = AsyncMock(return_value=False)
        mock_redis_client.ping = AsyncMock(return_value=True)
        
        # Create cache service with mocked Redis
        cache_service = CacheService()
        cache_service._redis_client = mock_redis_client
        cache_service._pool = mock_pool
        cache_service._is_available = True
        
        with patch.object(AIService, '_create_model'), patch.object(AIService, '_create_agent'):
            ai_service = AIService(cache_service=cache_service)
            proposals = [sample_proposal, complex_proposal]
            
            # Mock the actual AI calls
            with patch.object(ai_service, 'summarize_proposal') as mock_summarize:
                mock_summarize.side_effect = [
                    ProposalSummary(
                        proposal_id="prop-123",
                        title=sample_proposal.title,
                        summary="AI generated summary 1",
                        key_points=["Key point 1", "Key point 2"],
                        risk_level="LOW",
                        recommendation="APPROVE",
                        confidence_score=0.85,
                    ),
                    ProposalSummary(
                        proposal_id="prop-456", 
                        title=complex_proposal.title,
                        summary="AI generated summary 2",
                        key_points=["Complex point 1", "Complex point 2"],
                        risk_level="HIGH",
                        recommendation="REVIEW",
                        confidence_score=0.92,
                    ),
                ]

                # Act - First call (cache miss)
                result1 = await ai_service.summarize_multiple_proposals(proposals)

                # Assert - Verify AI was called and results are correct
                assert len(result1) == 2
                assert result1[0].summary == "AI generated summary 1"
                assert result1[1].summary == "AI generated summary 2"
                assert mock_summarize.call_count == 2
                
                # Verify cache operations occurred
                mock_redis_client.get.assert_called()  # Cache check
                mock_redis_client.setex.assert_called()  # Cache set
                mock_redis_client.set.assert_called()  # Lock acquire
                mock_redis_client.delete.assert_called()  # Lock release

                # Simulate cache hit for second call
                import json
                cached_data = [summary.dict() for summary in result1]
                mock_redis_client.get.return_value = json.dumps(cached_data)
                mock_summarize.reset_mock()

                # Act - Second call (cache hit)
                result2 = await ai_service.summarize_multiple_proposals(proposals)

                # Assert - Verify cached results returned, AI not called
                assert len(result2) == 2
                assert result2[0].summary == "AI generated summary 1"
                assert result2[1].summary == "AI generated summary 2"
                assert mock_summarize.call_count == 0  # AI not called

    @pytest.mark.asyncio
    async def test_concurrent_requests_with_locking(
        self, sample_proposal: Proposal
    ) -> None:
        """Test that concurrent requests use distributed locking correctly."""
        # Arrange
        mock_redis_client = AsyncMock()
        mock_pool = MagicMock()
        
        # First request gets lock, second waits
        lock_acquired = [True, False]  # First call gets lock, second doesn't
        mock_redis_client.set = AsyncMock(side_effect=lock_acquired)
        mock_redis_client.get = AsyncMock(return_value=None)  # Cache miss
        mock_redis_client.setex = AsyncMock(return_value=True)
        mock_redis_client.delete = AsyncMock(return_value=1)
        mock_redis_client.exists = AsyncMock(return_value=False)  # Lock released
        mock_redis_client.ping = AsyncMock(return_value=True)
        
        cache_service = CacheService()
        cache_service._redis_client = mock_redis_client
        cache_service._pool = mock_pool
        cache_service._is_available = True
        
        with patch.object(AIService, '_create_model'), patch.object(AIService, '_create_agent'):
            ai_service = AIService(cache_service=cache_service)
            proposals = [sample_proposal]
            
            # Mock AI processing with delay
            with patch.object(ai_service, 'summarize_proposal') as mock_summarize:
                async def slow_summarize(*args, **kwargs):
                    await asyncio.sleep(0.1)  # Simulate processing time
                    return ProposalSummary(
                        proposal_id="prop-123",
                        title=sample_proposal.title,
                        summary="Processed summary",
                        key_points=["Point 1"],
                        risk_level="LOW",
                        recommendation="APPROVE",
                        confidence_score=0.8,
                    )
                
                mock_summarize.side_effect = slow_summarize

                # Act - Simulate concurrent requests
                task1 = asyncio.create_task(
                    ai_service.summarize_multiple_proposals(proposals)
                )
                task2 = asyncio.create_task(
                    ai_service.summarize_multiple_proposals(proposals)
                )

                results = await asyncio.gather(task1, task2)

                # Assert - Both requests completed successfully
                assert len(results) == 2
                assert len(results[0]) == 1
                assert len(results[1]) == 1
                
                # Verify locking was attempted
                assert mock_redis_client.set.call_count >= 2  # Lock attempts

    @pytest.mark.asyncio
    async def test_cache_invalidation_on_content_change(
        self, sample_proposal: Proposal
    ) -> None:
        """Test that cache keys change when proposal content changes."""
        # Arrange
        mock_redis_client = AsyncMock()
        mock_pool = MagicMock()
        
        mock_redis_client.get = AsyncMock(return_value=None)
        mock_redis_client.setex = AsyncMock(return_value=True)
        mock_redis_client.set = AsyncMock(return_value=True)
        mock_redis_client.delete = AsyncMock(return_value=1)
        mock_redis_client.exists = AsyncMock(return_value=False)
        mock_redis_client.ping = AsyncMock(return_value=True)
        
        cache_service = CacheService()
        cache_service._redis_client = mock_redis_client
        cache_service._pool = mock_pool
        cache_service._is_available = True
        
        with patch.object(AIService, '_create_model'), patch.object(AIService, '_create_agent'):
            ai_service = AIService(cache_service=cache_service)
            
            with patch.object(ai_service, 'summarize_proposal') as mock_summarize:
                mock_summarize.return_value = ProposalSummary(
                    proposal_id="prop-123",
                    title=sample_proposal.title,
                    summary="Summary",
                    key_points=["Point 1"],
                    risk_level="LOW",
                    recommendation="APPROVE",
                    confidence_score=0.8,
                )

                # Act - First call with original proposal
                proposals1 = [sample_proposal]
                await ai_service.summarize_multiple_proposals(proposals1)
                
                # Get first cache key
                first_call = mock_redis_client.get.call_args_list[0]
                first_cache_key = first_call[0][0]

                # Modify proposal content
                modified_proposal = Proposal(
                    id=sample_proposal.id,
                    title=sample_proposal.title + " - MODIFIED",  # Changed title
                    description=sample_proposal.description,
                    state=sample_proposal.state,
                    created_at=sample_proposal.created_at,
                    start_block=sample_proposal.start_block,
                    end_block=sample_proposal.end_block,
                    votes_for=sample_proposal.votes_for,
                    votes_against=sample_proposal.votes_against,
                    votes_abstain=sample_proposal.votes_abstain,
                    dao_id=sample_proposal.dao_id,
                    dao_name=sample_proposal.dao_name,
                )

                mock_redis_client.reset_mock()

                # Act - Second call with modified proposal
                proposals2 = [modified_proposal]
                await ai_service.summarize_multiple_proposals(proposals2)
                
                # Get second cache key
                second_call = mock_redis_client.get.call_args_list[0]
                second_cache_key = second_call[0][0]

                # Assert - Cache keys should be different
                assert first_cache_key != second_cache_key

    @pytest.mark.asyncio
    async def test_cache_ttl_configuration(
        self, sample_proposal: Proposal
    ) -> None:
        """Test that cache TTL is properly configured to 4 hours."""
        # Arrange
        mock_redis_client = AsyncMock()
        mock_pool = MagicMock()
        
        mock_redis_client.get = AsyncMock(return_value=None)
        mock_redis_client.setex = AsyncMock(return_value=True)
        mock_redis_client.set = AsyncMock(return_value=True)
        mock_redis_client.delete = AsyncMock(return_value=1)
        mock_redis_client.exists = AsyncMock(return_value=False)
        mock_redis_client.ping = AsyncMock(return_value=True)
        
        cache_service = CacheService()
        cache_service._redis_client = mock_redis_client
        cache_service._pool = mock_pool
        cache_service._is_available = True
        
        with patch.object(AIService, '_create_model'), patch.object(AIService, '_create_agent'):
            ai_service = AIService(cache_service=cache_service)
            proposals = [sample_proposal]
            
            with patch.object(ai_service, 'summarize_proposal') as mock_summarize:
                mock_summarize.return_value = ProposalSummary(
                    proposal_id="prop-123",
                    title=sample_proposal.title,
                    summary="Summary",
                    key_points=["Point 1"],
                    risk_level="LOW",
                    recommendation="APPROVE",
                    confidence_score=0.8,
                )

                # Act
                await ai_service.summarize_multiple_proposals(proposals)

                # Assert - Verify TTL is set to 4 hours (14400 seconds)
                mock_redis_client.setex.assert_called()
                setex_call = mock_redis_client.setex.call_args
                cache_key, ttl, cache_data = setex_call[0]
                
                assert ttl == 14400  # 4 hours in seconds
                assert "ai_summary" in cache_key

    @pytest.mark.asyncio 
    async def test_graceful_fallback_when_cache_unavailable(
        self, sample_proposal: Proposal
    ) -> None:
        """Test that AI service works normally when cache is unavailable."""
        # Arrange - Create AI service without cache
        with patch.object(AIService, '_create_model'), patch.object(AIService, '_create_agent'):
            ai_service = AIService(cache_service=None)  # No cache service
            proposals = [sample_proposal]
            
            with patch.object(ai_service, 'summarize_proposal') as mock_summarize:
                mock_summarize.return_value = ProposalSummary(
                    proposal_id="prop-123",
                    title=sample_proposal.title,
                    summary="Summary without cache",
                    key_points=["Point 1"],
                    risk_level="LOW",
                    recommendation="APPROVE",
                    confidence_score=0.8,
                )

                # Act
                result = await ai_service.summarize_multiple_proposals(proposals)

                # Assert - Should work normally without caching
                assert len(result) == 1
                assert result[0].summary == "Summary without cache"
                mock_summarize.assert_called_once()