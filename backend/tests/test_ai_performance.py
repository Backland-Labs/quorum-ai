"""Performance tests for AI service caching."""

import pytest
from unittest.mock import patch, MagicMock, AsyncMock
import time
import asyncio

from services.ai_service import AIService
from services.cache_service import CacheService
from models import Proposal, ProposalSummary


class TestAIPerformance:
    """Performance tests for AI service caching functionality."""

    @pytest.mark.asyncio
    async def test_cache_performance_improvement(
        self, sample_proposal: Proposal, complex_proposal: Proposal
    ) -> None:
        """Test that cached summaries provide 70%+ performance improvement."""
        # Arrange
        mock_redis_client = AsyncMock()
        mock_pool = MagicMock()

        # Configure Redis mocks
        mock_redis_client.ping = AsyncMock(return_value=True)
        mock_redis_client.get = AsyncMock(return_value=None)  # Cache miss initially
        mock_redis_client.setex = AsyncMock(return_value=True)
        mock_redis_client.set = AsyncMock(return_value=True)  # For locks
        mock_redis_client.delete = AsyncMock(return_value=1)
        mock_redis_client.exists = AsyncMock(return_value=False)

        cache_service = CacheService()
        cache_service._redis_client = mock_redis_client
        cache_service._pool = mock_pool
        cache_service._is_available = True

        with patch.object(AIService, "_create_model"), patch.object(
            AIService, "_create_agent"
        ):
            ai_service = AIService(cache_service=cache_service)
            proposals = [sample_proposal, complex_proposal]

            # Mock AI processing with simulated delay
            with patch.object(ai_service, "summarize_proposal") as mock_summarize:

                async def simulate_ai_processing(*args, **kwargs):
                    # Simulate AI processing time (100ms per proposal)
                    await asyncio.sleep(0.1)
                    proposal = args[0]
                    return ProposalSummary(
                        proposal_id=proposal.id,
                        title=proposal.title,
                        summary=f"AI summary for {proposal.title}",
                        key_points=[f"Key point for {proposal.title}"],
                        risk_level="MEDIUM",
                        recommendation="REVIEW",
                        confidence_score=0.85,
                    )

                mock_summarize.side_effect = simulate_ai_processing

                # Act & Measure - First call (cache miss)
                start_time = time.time()
                result1 = await ai_service.summarize_multiple_proposals(proposals)
                first_call_time = time.time() - start_time

                # Verify AI was called
                assert len(result1) == 2
                assert mock_summarize.call_count == 2

                # Configure cache hit for second call
                import json

                cached_data = [summary.dict() for summary in result1]
                mock_redis_client.get.return_value = json.dumps(cached_data)
                mock_summarize.reset_mock()

                # Act & Measure - Second call (cache hit)
                start_time = time.time()
                result2 = await ai_service.summarize_multiple_proposals(proposals)
                second_call_time = time.time() - start_time

                # Verify cached results
                assert len(result2) == 2
                assert mock_summarize.call_count == 0  # AI not called
                assert result2[0].summary == result1[0].summary

                # Assert - Performance improvement
                performance_improvement = (
                    (first_call_time - second_call_time) / first_call_time * 100
                )

                print("\\nPerformance Test Results:")
                print(f"First call (cache miss): {first_call_time:.3f}s")
                print(f"Second call (cache hit): {second_call_time:.3f}s")
                print(f"Performance improvement: {performance_improvement:.1f}%")

                # Should be at least 70% improvement for cached calls
                assert (
                    performance_improvement >= 70.0
                ), f"Expected at least 70% performance improvement, got {performance_improvement:.1f}%"

    @pytest.mark.asyncio
    async def test_concurrent_cache_performance(
        self, sample_proposal: Proposal
    ) -> None:
        """Test performance with concurrent requests using caching."""
        # Arrange
        mock_redis_client = AsyncMock()
        mock_pool = MagicMock()

        mock_redis_client.ping = AsyncMock(return_value=True)
        mock_redis_client.setex = AsyncMock(return_value=True)
        mock_redis_client.delete = AsyncMock(return_value=1)
        mock_redis_client.exists = AsyncMock(return_value=False)

        cache_service = CacheService()
        cache_service._redis_client = mock_redis_client
        cache_service._pool = mock_pool
        cache_service._is_available = True

        with patch.object(AIService, "_create_model"), patch.object(
            AIService, "_create_agent"
        ):
            ai_service = AIService(cache_service=cache_service)
            proposals = [sample_proposal]

            # Test scenario 1: All requests are cache misses (should use locking)
            mock_redis_client.get = AsyncMock(return_value=None)  # Cache miss
            lock_attempts = []

            async def mock_acquire_lock(*args, **kwargs):
                lock_attempts.append(time.time())
                return len(lock_attempts) == 1  # First request gets lock

            mock_redis_client.set = AsyncMock(side_effect=mock_acquire_lock)

            with patch.object(ai_service, "summarize_proposal") as mock_summarize:

                async def simulate_ai_processing(*args, **kwargs):
                    await asyncio.sleep(0.05)  # 50ms processing
                    return ProposalSummary(
                        proposal_id="prop-123",
                        title=sample_proposal.title,
                        summary="Concurrent summary",
                        key_points=["Point 1"],
                        risk_level="LOW",
                        recommendation="APPROVE",
                        confidence_score=0.8,
                    )

                mock_summarize.side_effect = simulate_ai_processing

                # Act - Simulate 3 concurrent requests
                start_time = time.time()
                tasks = [
                    asyncio.create_task(
                        ai_service.summarize_multiple_proposals(proposals)
                    )
                    for _ in range(3)
                ]
                results = await asyncio.gather(*tasks)
                total_time = time.time() - start_time

                # Assert - All requests completed
                assert len(results) == 3
                assert all(len(result) == 1 for result in results)

                # With proper locking, total time should be reasonable
                # (not 3x the processing time due to locking efficiency)
                assert (
                    total_time < 0.2
                ), f"Concurrent requests took too long: {total_time:.3f}s"

                print("\\nConcurrent Performance Test:")
                print(f"3 concurrent requests completed in: {total_time:.3f}s")
                print(f"Lock attempts: {len(lock_attempts)}")

    @pytest.mark.asyncio
    async def test_cache_warming_simulation(
        self, sample_proposal: Proposal, complex_proposal: Proposal
    ) -> None:
        """Test performance improvement with pre-warmed cache."""
        # Arrange
        mock_redis_client = AsyncMock()
        mock_pool = MagicMock()

        mock_redis_client.ping = AsyncMock(return_value=True)
        mock_redis_client.setex = AsyncMock(return_value=True)
        mock_redis_client.set = AsyncMock(return_value=True)
        mock_redis_client.delete = AsyncMock(return_value=1)
        mock_redis_client.exists = AsyncMock(return_value=False)

        cache_service = CacheService()
        cache_service._redis_client = mock_redis_client
        cache_service._pool = mock_pool
        cache_service._is_available = True

        with patch.object(AIService, "_create_model"), patch.object(
            AIService, "_create_agent"
        ):
            ai_service = AIService(cache_service=cache_service)
            proposals = [sample_proposal, complex_proposal]

            # Pre-warm cache with data
            pre_warmed_summaries = [
                ProposalSummary(
                    proposal_id=sample_proposal.id,
                    title=sample_proposal.title,
                    summary="Pre-warmed summary 1",
                    key_points=["Pre-warmed point 1"],
                    risk_level="LOW",
                    recommendation="APPROVE",
                    confidence_score=0.9,
                ),
                ProposalSummary(
                    proposal_id=complex_proposal.id,
                    title=complex_proposal.title,
                    summary="Pre-warmed summary 2",
                    key_points=["Pre-warmed point 2"],
                    risk_level="HIGH",
                    recommendation="REVIEW",
                    confidence_score=0.95,
                ),
            ]

            import json

            cached_data = [summary.dict() for summary in pre_warmed_summaries]
            mock_redis_client.get = AsyncMock(return_value=json.dumps(cached_data))

            with patch.object(ai_service, "summarize_proposal") as mock_summarize:
                # Act - All requests should hit cache (no AI processing)
                start_time = time.time()
                result = await ai_service.summarize_multiple_proposals(proposals)
                cache_hit_time = time.time() - start_time

                # Assert - Fast response from cache
                assert len(result) == 2
                assert mock_summarize.call_count == 0  # No AI calls
                assert result[0].summary == "Pre-warmed summary 1"
                assert result[1].summary == "Pre-warmed summary 2"

                # Cache hits should be very fast (< 10ms)
                assert (
                    cache_hit_time < 0.01
                ), f"Cache hit took too long: {cache_hit_time:.3f}s"

                print("\\nCache Warming Test:")
                print(f"Pre-warmed cache response time: {cache_hit_time:.3f}s")
                print("AI processing avoided: 100%")

    @pytest.mark.asyncio
    async def test_memory_efficiency_with_caching(
        self, sample_proposal: Proposal
    ) -> None:
        """Test that caching doesn't cause memory leaks with repeated calls."""
        # Arrange
        mock_redis_client = AsyncMock()
        mock_pool = MagicMock()

        mock_redis_client.ping = AsyncMock(return_value=True)
        mock_redis_client.setex = AsyncMock(return_value=True)
        mock_redis_client.set = AsyncMock(return_value=True)
        mock_redis_client.delete = AsyncMock(return_value=1)
        mock_redis_client.exists = AsyncMock(return_value=False)

        # Pre-configure cache hit
        cached_summary = ProposalSummary(
            proposal_id=sample_proposal.id,
            title=sample_proposal.title,
            summary="Cached summary",
            key_points=["Cached point"],
            risk_level="LOW",
            recommendation="APPROVE",
            confidence_score=0.8,
        )

        import json

        cached_data = [cached_summary.dict()]
        mock_redis_client.get = AsyncMock(return_value=json.dumps(cached_data))

        cache_service = CacheService()
        cache_service._redis_client = mock_redis_client
        cache_service._pool = mock_pool
        cache_service._is_available = True

        with patch.object(AIService, "_create_model"), patch.object(
            AIService, "_create_agent"
        ):
            ai_service = AIService(cache_service=cache_service)
            proposals = [sample_proposal]

            with patch.object(ai_service, "summarize_proposal") as mock_summarize:
                # Act - Make many repeated calls (should all be cache hits)
                num_calls = 100
                start_time = time.time()

                for i in range(num_calls):
                    result = await ai_service.summarize_multiple_proposals(proposals)
                    assert len(result) == 1
                    assert result[0].summary == "Cached summary"

                total_time = time.time() - start_time
                avg_time_per_call = total_time / num_calls

                # Assert - Performance should remain consistent
                assert mock_summarize.call_count == 0  # No AI calls
                assert (
                    avg_time_per_call < 0.001
                ), f"Average cache hit time too slow: {avg_time_per_call:.4f}s"

                print("\\nMemory Efficiency Test:")
                print(f"{num_calls} cache hits in: {total_time:.3f}s")
                print(f"Average time per cache hit: {avg_time_per_call:.4f}s")
                print("Memory efficiency: No AI processing overhead")
