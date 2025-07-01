"""Tests for TallyService caching functionality using TDD approach."""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime
from typing import List, Dict, Any

from services.tally_service import TallyService
from services.cache_service import CacheService
from models import Proposal, ProposalState


class TestTallyServiceTopOrganizationsCaching:
    """Test caching for get_top_organizations_with_proposals method using TDD."""

    @pytest.fixture
    def mock_cache_service(self) -> AsyncMock:
        """Mock cache service for testing."""
        cache_service = AsyncMock(spec=CacheService)
        cache_service.is_available = True
        return cache_service

    @pytest.fixture
    def tally_service_with_cache(self, mock_cache_service: AsyncMock) -> TallyService:
        """Create TallyService instance with mocked cache service."""
        service = TallyService(cache_service=mock_cache_service)
        return service

    @pytest.fixture
    def mock_organizations_data(self) -> List[Dict[str, Any]]:
        """Mock organization data structure."""
        return [
            {
                "organization": {
                    "id": "org-1",
                    "name": "Test DAO 1",
                    "slug": "test-dao-1",
                    "chain_ids": ["1"],
                    "token_ids": ["token-1"],
                    "governor_ids": ["gov-1"],
                    "has_active_proposals": True,
                    "proposals_count": 10,
                    "delegates_count": 100,
                    "delegates_votes_count": "1000000",
                    "token_owners_count": 500,
                },
                "proposals": [
                    Proposal(
                        id="prop-1",
                        title="Test Proposal 1",
                        description="Description 1",
                        state=ProposalState.ACTIVE,
                        created_at=datetime.now(),
                        start_block=1000,
                        end_block=2000,
                        votes_for="1000000",
                        votes_against="250000",
                        votes_abstain="50000",
                        dao_id="dao-1",
                        dao_name="Test DAO",
                    )
                ],
            }
        ]

    async def test_get_top_organizations_cache_miss_calls_api_and_caches_result(
        self,
        tally_service_with_cache: TallyService,
        mock_cache_service: AsyncMock,
        mock_organizations_data: List[Dict[str, Any]],
    ) -> None:
        """Test that on cache miss, API is called and result is cached with 2-hour TTL."""
        # Arrange - Cache miss scenario
        mock_cache_service.get.return_value = None
        mock_cache_service.set.return_value = True
        
        # Mock the internal API calls
        with patch.object(
            tally_service_with_cache, '_get_organizations_data'
        ) as mock_get_data:
            mock_get_data.return_value = mock_organizations_data
            
            # Act
            result = await tally_service_with_cache.get_top_organizations_with_proposals()
            
            # Assert - API was called
            mock_get_data.assert_called_once()
            
            # Assert - Cache was checked
            expected_cache_key = "cache:get_top_organizations_with_proposals:noargs:*"
            mock_cache_service.get.assert_called_once()
            
            # Assert - Result was cached with 2-hour TTL (7200 seconds)
            mock_cache_service.set.assert_called_once()
            cache_call_args = mock_cache_service.set.call_args
            assert cache_call_args[1]['expire_seconds'] == 7200  # 2 hours
            
            # Assert - Correct result returned
            assert result == mock_organizations_data

    async def test_get_top_organizations_cache_hit_returns_cached_data_without_api_call(
        self,
        tally_service_with_cache: TallyService,
        mock_cache_service: AsyncMock,
        mock_organizations_data: List[Dict[str, Any]],
    ) -> None:
        """Test that on cache hit, cached data is returned without API call."""
        # Arrange - Cache hit scenario - need to serialize for cache
        from utils.cache_utils import serialize_for_cache
        serialized_data = serialize_for_cache(mock_organizations_data)
        mock_cache_service.get.return_value = serialized_data
        
        # Mock the internal API calls to ensure they're not called
        with patch.object(
            tally_service_with_cache, '_get_organizations_data'
        ) as mock_get_data:
            
            # Act
            result = await tally_service_with_cache.get_top_organizations_with_proposals()
            
            # Assert - API was NOT called
            mock_get_data.assert_not_called()
            
            # Assert - Cache was checked
            mock_cache_service.get.assert_called_once()
            
            # Assert - Result was NOT cached again (no set call)
            mock_cache_service.set.assert_not_called()
            
            # Assert - Cached result returned (Proposal objects become dicts after serialization)
            assert len(result) == len(mock_organizations_data)
            assert result[0]["organization"] == mock_organizations_data[0]["organization"]
            # Check that proposals are returned as dicts (serialized)
            assert len(result[0]["proposals"]) == 1
            assert result[0]["proposals"][0]["id"] == "prop-1"

    async def test_get_top_organizations_cache_unavailable_calls_api_directly(
        self,
        tally_service_with_cache: TallyService,
        mock_cache_service: AsyncMock,
        mock_organizations_data: List[Dict[str, Any]],
    ) -> None:
        """Test that when cache is unavailable, API is called directly."""
        # Arrange - Cache unavailable
        mock_cache_service.is_available = False
        
        # Mock the internal API calls
        with patch.object(
            tally_service_with_cache, '_get_organizations_data'
        ) as mock_get_data:
            mock_get_data.return_value = mock_organizations_data
            
            # Act
            result = await tally_service_with_cache.get_top_organizations_with_proposals()
            
            # Assert - API was called
            mock_get_data.assert_called_once()
            
            # Assert - Cache was NOT checked
            mock_cache_service.get.assert_not_called()
            
            # Assert - Result was NOT cached
            mock_cache_service.set.assert_not_called()
            
            # Assert - Correct result returned
            assert result == mock_organizations_data

    async def test_get_top_organizations_cache_error_falls_back_to_api(
        self,
        tally_service_with_cache: TallyService,
        mock_cache_service: AsyncMock,
        mock_organizations_data: List[Dict[str, Any]],
    ) -> None:
        """Test that cache errors result in fallback to API call."""
        # Arrange - Cache get raises exception
        mock_cache_service.get.side_effect = Exception("Redis connection error")
        
        # Mock the internal API calls
        with patch.object(
            tally_service_with_cache, '_get_organizations_data'
        ) as mock_get_data:
            mock_get_data.return_value = mock_organizations_data
            
            # Act
            result = await tally_service_with_cache.get_top_organizations_with_proposals()
            
            # Assert - API was called
            mock_get_data.assert_called_once()
            
            # Assert - Correct result returned despite cache error
            assert result == mock_organizations_data

    async def test_get_top_organizations_logs_cache_hit_and_miss_events(
        self,
        tally_service_with_cache: TallyService,
        mock_cache_service: AsyncMock,
        mock_organizations_data: List[Dict[str, Any]],
    ) -> None:
        """Test that cache hit/miss events are properly logged."""
        with patch('services.tally_service.logfire') as mock_logfire:
            # Test cache miss scenario
            mock_cache_service.get.return_value = None
            mock_cache_service.set.return_value = True
            
            with patch.object(
                tally_service_with_cache, '_get_organizations_data'
            ) as mock_get_data:
                mock_get_data.return_value = mock_organizations_data
                
                # Act - Cache miss
                await tally_service_with_cache.get_top_organizations_with_proposals()
                
                # Assert - Cache miss logged
                mock_logfire.info.assert_any_call(
                    "Cache miss for get_top_organizations_with_proposals"
                )
                
            # Reset mocks for cache hit test
            mock_logfire.reset_mock()
            mock_cache_service.get.return_value = mock_organizations_data
            
            # Act - Cache hit
            await tally_service_with_cache.get_top_organizations_with_proposals()
            
            # Assert - Cache hit logged
            mock_logfire.info.assert_any_call(
                "Cache hit for get_top_organizations_with_proposals"
            )


class TestTallyServiceOrganizationOverviewCaching:
    """Test caching for get_organization_overview method using TDD."""

    @pytest.fixture
    def mock_cache_service(self) -> AsyncMock:
        """Mock cache service for testing."""
        cache_service = AsyncMock(spec=CacheService)
        cache_service.is_available = True
        return cache_service

    @pytest.fixture
    def tally_service_with_cache(self, mock_cache_service: AsyncMock) -> TallyService:
        """Create TallyService instance with mocked cache service."""
        service = TallyService(cache_service=mock_cache_service)
        return service

    @pytest.fixture
    def mock_overview_data(self) -> Dict[str, Any]:
        """Mock organization overview data."""
        return {
            "organization_id": "org-123",
            "organization_name": "Test DAO",
            "organization_slug": "test-dao",
            "description": "A test DAO organization",
            "delegate_count": 150,
            "token_holder_count": 1000,
            "total_proposals_count": 50,
            "proposal_counts_by_status": {"ACTIVE": 3},
            "recent_activity_count": 3,
            "governance_participation_rate": 0.15,
        }

    async def test_get_organization_overview_cache_miss_calls_api_and_caches_result(
        self,
        tally_service_with_cache: TallyService,
        mock_cache_service: AsyncMock,
        mock_overview_data: Dict[str, Any],
    ) -> None:
        """Test that on cache miss, API is called and result is cached with 2-hour TTL."""
        # Arrange - Cache miss scenario
        org_id = "test-dao"
        mock_cache_service.get.return_value = None
        mock_cache_service.set.return_value = True
        
        # Mock the internal API calls
        with patch.object(
            tally_service_with_cache, '_fetch_organization_data'
        ) as mock_fetch_data, patch.object(
            tally_service_with_cache, '_build_organization_overview_response'
        ) as mock_build_response:
            mock_fetch_data.return_value = {"id": "org-123", "name": "Test DAO"}
            mock_build_response.return_value = mock_overview_data
            
            # Act
            result = await tally_service_with_cache.get_organization_overview(org_id)
            
            # Assert - API was called
            mock_fetch_data.assert_called_once_with(org_id)
            mock_build_response.assert_called_once()
            
            # Assert - Cache was checked with correct key
            mock_cache_service.get.assert_called_once()
            cache_get_key = mock_cache_service.get.call_args[0][0]
            assert "get_organization_overview" in cache_get_key
            assert org_id in cache_get_key
            
            # Assert - Result was cached with 2-hour TTL (7200 seconds)
            mock_cache_service.set.assert_called_once()
            cache_call_args = mock_cache_service.set.call_args
            assert cache_call_args[1]['expire_seconds'] == 7200  # 2 hours
            
            # Assert - Correct result returned
            assert result == mock_overview_data

    async def test_get_organization_overview_cache_hit_returns_cached_data(
        self,
        tally_service_with_cache: TallyService,
        mock_cache_service: AsyncMock,
        mock_overview_data: Dict[str, Any],
    ) -> None:
        """Test that on cache hit, cached data is returned without API call."""
        # Arrange - Cache hit scenario - need to serialize for cache
        org_id = "test-dao"
        from utils.cache_utils import serialize_for_cache
        serialized_data = serialize_for_cache(mock_overview_data)
        mock_cache_service.get.return_value = serialized_data
        
        # Mock the internal API calls to ensure they're not called
        with patch.object(
            tally_service_with_cache, '_fetch_organization_data'
        ) as mock_fetch_data:
            
            # Act
            result = await tally_service_with_cache.get_organization_overview(org_id)
            
            # Assert - API was NOT called
            mock_fetch_data.assert_not_called()
            
            # Assert - Cache was checked
            mock_cache_service.get.assert_called_once()
            
            # Assert - Result was NOT cached again (no set call)
            mock_cache_service.set.assert_not_called()
            
            # Assert - Cached result returned
            assert result == mock_overview_data


class TestTallyServiceProposalByIdCaching:
    """Test caching for get_proposal_by_id method with dynamic TTL using TDD."""

    @pytest.fixture
    def mock_cache_service(self) -> AsyncMock:
        """Mock cache service for testing."""
        cache_service = AsyncMock(spec=CacheService)
        cache_service.is_available = True
        return cache_service

    @pytest.fixture
    def tally_service_with_cache(self, mock_cache_service: AsyncMock) -> TallyService:
        """Create TallyService instance with mocked cache service."""
        service = TallyService(cache_service=mock_cache_service)
        return service

    @pytest.fixture
    def active_proposal(self) -> Proposal:
        """Mock active proposal data."""
        return Proposal(
            id="prop-active-123",
            title="Active Test Proposal",
            description="An active proposal for testing",
            state=ProposalState.ACTIVE,
            created_at=datetime.now(),
            start_block=1000,
            end_block=2000,
            votes_for="1000000",
            votes_against="250000",
            votes_abstain="50000",
            dao_id="dao-123",
            dao_name="Test DAO",
        )

    @pytest.fixture
    def completed_proposal(self) -> Proposal:
        """Mock completed proposal data."""
        return Proposal(
            id="prop-completed-456",
            title="Completed Test Proposal",
            description="A completed proposal for testing",
            state=ProposalState.SUCCEEDED,
            created_at=datetime.now(),
            start_block=1000,
            end_block=2000,
            votes_for="2000000",
            votes_against="100000",
            votes_abstain="25000",
            dao_id="dao-456",
            dao_name="Test DAO 2",
        )

    async def test_get_proposal_by_id_active_proposal_cached_with_30min_ttl(
        self,
        tally_service_with_cache: TallyService,
        mock_cache_service: AsyncMock,
        active_proposal: Proposal,
    ) -> None:
        """Test that active proposals are cached with 30-minute TTL."""
        # Arrange - Cache miss scenario
        proposal_id = "prop-active-123"
        mock_cache_service.get.return_value = None
        mock_cache_service.set.return_value = True
        
        # Mock the internal API calls
        with patch.object(
            tally_service_with_cache, '_make_request'
        ) as mock_make_request, patch.object(
            tally_service_with_cache, '_create_proposal_from_api_data'
        ) as mock_create_proposal:
            mock_make_request.return_value = {"data": {"proposal": {"id": "test"}}}
            mock_create_proposal.return_value = active_proposal
            
            # Act
            result = await tally_service_with_cache.get_proposal_by_id(proposal_id)
            
            # Assert - API was called
            mock_make_request.assert_called_once()
            
            # Assert - Cache was checked
            mock_cache_service.get.assert_called_once()
            
            # Assert - Result was cached with 30-minute TTL (1800 seconds)
            mock_cache_service.set.assert_called_once()
            cache_call_args = mock_cache_service.set.call_args
            assert cache_call_args[1]['expire_seconds'] == 1800  # 30 minutes
            
            # Assert - Correct result returned
            assert result == active_proposal

    async def test_get_proposal_by_id_completed_proposal_cached_with_6hour_ttl(
        self,
        tally_service_with_cache: TallyService,
        mock_cache_service: AsyncMock,
        completed_proposal: Proposal,
    ) -> None:
        """Test that completed proposals are cached with 6-hour TTL."""
        # Arrange - Cache miss scenario
        proposal_id = "prop-completed-456"
        mock_cache_service.get.return_value = None
        mock_cache_service.set.return_value = True
        
        # Mock the internal API calls
        with patch.object(
            tally_service_with_cache, '_make_request'
        ) as mock_make_request, patch.object(
            tally_service_with_cache, '_create_proposal_from_api_data'
        ) as mock_create_proposal:
            mock_make_request.return_value = {"data": {"proposal": {"id": "test"}}}
            mock_create_proposal.return_value = completed_proposal
            
            # Act
            result = await tally_service_with_cache.get_proposal_by_id(proposal_id)
            
            # Assert - API was called
            mock_make_request.assert_called_once()
            
            # Assert - Cache was checked
            mock_cache_service.get.assert_called_once()
            
            # Assert - Result was cached with 6-hour TTL (21600 seconds)
            mock_cache_service.set.assert_called_once()
            cache_call_args = mock_cache_service.set.call_args
            assert cache_call_args[1]['expire_seconds'] == 21600  # 6 hours
            
            # Assert - Correct result returned
            assert result == completed_proposal

    async def test_get_proposal_by_id_cache_hit_returns_cached_data(
        self,
        tally_service_with_cache: TallyService,
        mock_cache_service: AsyncMock,
        active_proposal: Proposal,
    ) -> None:
        """Test that on cache hit, cached proposal data is returned without API call."""
        # Arrange - Cache hit scenario - need to serialize for cache
        proposal_id = "prop-active-123"
        from utils.cache_utils import serialize_for_cache
        serialized_data = serialize_for_cache(active_proposal)
        mock_cache_service.get.return_value = serialized_data
        
        # Mock the internal API calls to ensure they're not called
        with patch.object(
            tally_service_with_cache, '_make_request'
        ) as mock_make_request:
            
            # Act
            result = await tally_service_with_cache.get_proposal_by_id(proposal_id)
            
            # Assert - API was NOT called
            mock_make_request.assert_not_called()
            
            # Assert - Cache was checked
            mock_cache_service.get.assert_called_once()
            
            # Assert - Result was NOT cached again (no set call)
            mock_cache_service.set.assert_not_called()
            
            # Assert - Cached result returned
            assert result == active_proposal


class TestTallyServiceCacheInvalidation:
    """Test cache invalidation functionality using TDD."""

    @pytest.fixture
    def mock_cache_service(self) -> AsyncMock:
        """Mock cache service for testing."""
        cache_service = AsyncMock(spec=CacheService)
        cache_service.is_available = True
        return cache_service

    @pytest.fixture
    def tally_service_with_cache(self, mock_cache_service: AsyncMock) -> TallyService:
        """Create TallyService instance with mocked cache service."""
        service = TallyService(cache_service=mock_cache_service)
        return service

    async def test_invalidate_organization_cache_clears_related_cache_entries(
        self,
        tally_service_with_cache: TallyService,
        mock_cache_service: AsyncMock,
    ) -> None:
        """Test that invalidating organization cache clears all related entries."""
        # Arrange
        org_id = "test-org-123"
        # Mock keys to return different results for different patterns
        def keys_side_effect(pattern):
            if "test-org-123" in pattern:
                return ["cache:get_organization_overview:test-org-123:abcd1234"]
            elif "get_top_organizations_with_proposals" in pattern:
                return ["cache:get_top_organizations_with_proposals:noargs:xyz9876"]
            return []
        
        mock_cache_service.keys.side_effect = keys_side_effect
        mock_cache_service.delete.return_value = 1  # Each call deletes 1 key
        
        # Act
        deleted_count = await tally_service_with_cache.invalidate_organization_cache(org_id)
        
        # Assert - Cache service was called to find and delete related keys
        mock_cache_service.keys.assert_called()
        mock_cache_service.delete.assert_called()
        assert deleted_count == 2

    async def test_invalidate_proposal_cache_clears_related_cache_entries(
        self,
        tally_service_with_cache: TallyService,
        mock_cache_service: AsyncMock,
    ) -> None:
        """Test that invalidating proposal cache clears all related entries."""
        # Arrange
        proposal_id = "prop-456"
        mock_cache_service.keys.return_value = [
            "cache:get_proposal_by_id:prop-456:xyz789",
        ]
        mock_cache_service.delete.return_value = 1
        
        # Act
        deleted_count = await tally_service_with_cache.invalidate_proposal_cache(proposal_id)
        
        # Assert - Cache service was called to find and delete related keys
        mock_cache_service.keys.assert_called()
        mock_cache_service.delete.assert_called()
        assert deleted_count == 1

    async def test_invalidate_all_cache_clears_all_tally_cache_entries(
        self,
        tally_service_with_cache: TallyService,
        mock_cache_service: AsyncMock,
    ) -> None:
        """Test that invalidating all cache clears all Tally-related entries."""
        # Arrange
        mock_cache_service.keys.return_value = [
            "cache:get_organization_overview:org-1:hash123",
            "cache:get_proposal_by_id:prop-1:hash456",
            "cache:get_top_organizations_with_proposals:noargs:hash789",
        ]
        mock_cache_service.delete.return_value = 3
        
        # Act
        deleted_count = await tally_service_with_cache.invalidate_all_cache()
        
        # Assert - All Tally cache entries were deleted
        mock_cache_service.keys.assert_called_with("cache:*")
        mock_cache_service.delete.assert_called()
        assert deleted_count == 3

    async def test_cache_invalidation_handles_cache_service_unavailable(
        self,
        tally_service_with_cache: TallyService,
        mock_cache_service: AsyncMock,
    ) -> None:
        """Test that cache invalidation handles unavailable cache service gracefully."""
        # Arrange
        mock_cache_service.is_available = False
        
        # Act
        deleted_count = await tally_service_with_cache.invalidate_organization_cache("org-123")
        
        # Assert - No operations performed, zero returned
        mock_cache_service.keys.assert_not_called()
        mock_cache_service.delete.assert_not_called()
        assert deleted_count == 0

    async def test_cache_invalidation_handles_errors_gracefully(
        self,
        tally_service_with_cache: TallyService,
        mock_cache_service: AsyncMock,
    ) -> None:
        """Test that cache invalidation handles Redis errors gracefully."""
        # Arrange
        mock_cache_service.keys.side_effect = Exception("Redis connection error")
        
        # Act
        deleted_count = await tally_service_with_cache.invalidate_organization_cache("org-123")
        
        # Assert - Error handled gracefully, zero returned
        assert deleted_count == 0


class TestTallyServiceCacheWarming:
    """Test cache warming functionality using TDD."""

    @pytest.fixture
    def mock_cache_service(self) -> AsyncMock:
        """Mock cache service for testing."""
        cache_service = AsyncMock(spec=CacheService)
        cache_service.is_available = True
        return cache_service

    @pytest.fixture
    def tally_service_with_cache(self, mock_cache_service: AsyncMock) -> TallyService:
        """Create TallyService instance with mocked cache service."""
        service = TallyService(cache_service=mock_cache_service)
        return service

    async def test_warm_top_organizations_cache_preloads_data(
        self,
        tally_service_with_cache: TallyService,
        mock_cache_service: AsyncMock,
    ) -> None:
        """Test that cache warming preloads top organizations data."""
        # Arrange
        mock_cache_service.exists.return_value = False  # Cache not warmed yet
        mock_cache_service.set.return_value = True
        
        # Mock the data fetching method
        with patch.object(
            tally_service_with_cache, '_get_organizations_data'
        ) as mock_get_data:
            mock_get_data.return_value = [{"organization": {"id": "org-1"}, "proposals": []}]
            
            # Act
            result = await tally_service_with_cache.warm_top_organizations_cache()
            
            # Assert - Data was fetched and cached
            mock_get_data.assert_called_once()
            mock_cache_service.set.assert_called_once()
            
            # Assert - TTL was set to 2 hours
            cache_call_args = mock_cache_service.set.call_args
            assert cache_call_args[1]['expire_seconds'] == 7200  # 2 hours
            
            assert result is True

    async def test_warm_top_organizations_cache_skips_if_already_cached(
        self,
        tally_service_with_cache: TallyService,
        mock_cache_service: AsyncMock,
    ) -> None:
        """Test that cache warming skips if data is already cached."""
        # Arrange
        mock_cache_service.exists.return_value = True  # Cache already warmed
        
        # Mock the data fetching method
        with patch.object(
            tally_service_with_cache, '_get_organizations_data'
        ) as mock_get_data:
            
            # Act
            result = await tally_service_with_cache.warm_top_organizations_cache()
            
            # Assert - No data fetching or caching occurred
            mock_get_data.assert_not_called()
            mock_cache_service.set.assert_not_called()
            
            assert result is True

    async def test_warm_organization_overview_cache_preloads_top_3_orgs(
        self,
        tally_service_with_cache: TallyService,
        mock_cache_service: AsyncMock,
    ) -> None:
        """Test that cache warming preloads overview data for top 3 organizations."""
        # Arrange
        top_orgs = ["dao1", "dao2", "dao3"]
        
        with patch('config.settings') as mock_settings:
            mock_settings.top_organizations = top_orgs
            mock_cache_service.exists.return_value = False  # Cache not warmed
            mock_cache_service.set.return_value = True
            
            # Mock the overview fetching
            with patch.object(
                tally_service_with_cache, '_fetch_organization_data'
            ) as mock_fetch_data, patch.object(
                tally_service_with_cache, '_build_organization_overview_response'
            ) as mock_build_response:
                mock_fetch_data.return_value = {"id": "org-1", "name": "Test DAO"}
                mock_build_response.return_value = {"organization_id": "org-1"}
                
                # Act
                result = await tally_service_with_cache.warm_organization_overview_cache()
                
                # Assert - Called for each of the 3 organizations
                assert mock_fetch_data.call_count == 3
                assert mock_cache_service.set.call_count == 3
                
                assert result is True

    async def test_cache_warming_handles_cache_service_unavailable(
        self,
        tally_service_with_cache: TallyService,
        mock_cache_service: AsyncMock,
    ) -> None:
        """Test that cache warming handles unavailable cache service gracefully."""
        # Arrange
        mock_cache_service.is_available = False
        
        # Act
        result = await tally_service_with_cache.warm_top_organizations_cache()
        
        # Assert - No operations performed, False returned
        mock_cache_service.exists.assert_not_called()
        mock_cache_service.set.assert_not_called()
        assert result is False

    async def test_cache_warming_handles_errors_gracefully(
        self,
        tally_service_with_cache: TallyService,
        mock_cache_service: AsyncMock,
    ) -> None:
        """Test that cache warming handles errors gracefully."""
        # Arrange
        mock_cache_service.exists.side_effect = Exception("Redis connection error")
        
        # Act
        result = await tally_service_with_cache.warm_top_organizations_cache()
        
        # Assert - Error handled gracefully, False returned
        assert result is False