"""Tests for FundsService balance checking and deficit calculation."""

import pytest
from unittest.mock import Mock, patch, MagicMock
from httpx import ASGITransport, AsyncClient

from services.funds_service import FundsService, ZERO_ADDRESS


class TestFundsService:
    """Test suite for FundsService."""

    def setup_method(self):
        """Set up test fixtures."""
        self.service = FundsService()

    def test_calculate_deficit_below_threshold(self):
        """Test deficit calculation when balance is below threshold."""
        balance = 1000
        threshold = "5000"
        topup = "10000"

        deficit = self.service.calculate_deficit(balance, threshold, topup)

        # deficit = max(10000 - 1000, 0) = 9000
        assert deficit == 9000

    def test_calculate_deficit_above_threshold(self):
        """Test deficit calculation when balance is above threshold."""
        balance = 10000
        threshold = "5000"
        topup = "10000"

        deficit = self.service.calculate_deficit(balance, threshold, topup)

        # balance >= threshold, so deficit = 0
        assert deficit == 0

    def test_calculate_deficit_at_threshold(self):
        """Test deficit calculation when balance equals threshold."""
        balance = 5000
        threshold = "5000"
        topup = "10000"

        deficit = self.service.calculate_deficit(balance, threshold, topup)

        # balance >= threshold, so deficit = 0
        assert deficit == 0

    def test_calculate_deficit_balance_exceeds_topup(self):
        """Test deficit when balance below threshold but exceeds topup amount."""
        # Edge case: balance below threshold but above topup
        # This shouldn't happen in practice, but test it anyway
        balance = 100
        threshold = "5000"
        topup = "50"  # topup < balance

        deficit = self.service.calculate_deficit(balance, threshold, topup)

        # deficit = max(50 - 100, 0) = 0
        assert deficit == 0

    @patch("services.funds_service.get_w3")
    def test_fetch_native_balance(self, mock_get_w3):
        """Test fetching native token (ETH) balance."""
        mock_w3 = MagicMock()
        mock_w3.eth.get_balance.return_value = 1000000000000000000  # 1 ETH in wei
        mock_get_w3.return_value = mock_w3

        balance, decimals = self.service.fetch_balance(
            "base",
            "0x1234567890123456789012345678901234567890",
            ZERO_ADDRESS,
        )

        assert balance == 1000000000000000000
        assert decimals == 18
        mock_w3.eth.get_balance.assert_called_once()

    @patch("services.funds_service.get_w3")
    def test_fetch_erc20_balance(self, mock_get_w3):
        """Test fetching ERC20 token balance."""
        mock_w3 = MagicMock()
        mock_contract = MagicMock()
        mock_contract.functions.balanceOf.return_value.call.return_value = 1000000  # 1 USDC
        mock_contract.functions.decimals.return_value.call.return_value = 6

        mock_w3.eth.contract.return_value = mock_contract
        mock_get_w3.return_value = mock_w3

        usdc_address = "0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913"
        balance, decimals = self.service.fetch_balance(
            "base",
            "0x1234567890123456789012345678901234567890",
            usdc_address,
        )

        assert balance == 1000000
        assert decimals == 6

    @patch("services.funds_service.get_w3")
    def test_fetch_balance_rpc_error(self, mock_get_w3):
        """Test handling of RPC errors during balance fetch."""
        mock_get_w3.side_effect = Exception("RPC connection failed")

        with pytest.raises(Exception, match="RPC connection failed"):
            self.service.fetch_balance(
                "base",
                "0x1234567890123456789012345678901234567890",
                ZERO_ADDRESS,
            )

    @patch.object(FundsService, "fetch_balance")
    def test_compute_funds_status_empty_requirements(self, mock_fetch):
        """Test compute_funds_status with empty requirements."""
        requirements = {}

        result = self.service.compute_funds_status(requirements)

        assert result == {}
        mock_fetch.assert_not_called()

    @patch.object(FundsService, "fetch_balance")
    def test_compute_funds_status_all_healthy(self, mock_fetch):
        """Test compute_funds_status when all balances are healthy."""
        mock_fetch.return_value = (10000000000000000000, 18)  # 10 ETH

        requirements = {
            "base": {
                "0x07edA994E013AbC8619A5038455db3A6FBdd2Bca": {
                    ZERO_ADDRESS: {
                        "threshold": "1000000000000000000",  # 1 ETH
                        "topup": "5000000000000000000",  # 5 ETH
                    }
                }
            }
        }

        result = self.service.compute_funds_status(requirements)

        # Balance (10 ETH) >= threshold (1 ETH), so no deficit
        assert result == {}

    @patch.object(FundsService, "fetch_balance")
    def test_compute_funds_status_with_deficit(self, mock_fetch):
        """Test compute_funds_status when a deficit exists."""
        mock_fetch.return_value = (100000000000000, 18)  # 0.0001 ETH

        requirements = {
            "base": {
                "0x07edA994E013AbC8619A5038455db3A6FBdd2Bca": {
                    ZERO_ADDRESS: {
                        "threshold": "1000000000000000000",  # 1 ETH
                        "topup": "5000000000000000000",  # 5 ETH
                    }
                }
            }
        }

        result = self.service.compute_funds_status(requirements)

        # Balance (0.0001 ETH) < threshold (1 ETH)
        # deficit = topup - balance = 5 ETH - 0.0001 ETH
        expected_deficit = 5000000000000000000 - 100000000000000
        assert result == {
            "base": {
                "0x07edA994E013AbC8619A5038455db3A6FBdd2Bca": {
                    ZERO_ADDRESS: str(expected_deficit)
                }
            }
        }

    @patch.object(FundsService, "fetch_balance")
    def test_compute_funds_status_multiple_chains(self, mock_fetch):
        """Test compute_funds_status with multiple chains."""
        # Return different balances for different calls
        mock_fetch.side_effect = [
            (100000000000000, 18),  # Low balance (deficit)
            (10000000000000000000, 18),  # High balance (healthy)
        ]

        requirements = {
            "base": {
                "0xAddress1": {
                    ZERO_ADDRESS: {
                        "threshold": "1000000000000000000",
                        "topup": "5000000000000000000",
                    }
                }
            },
            "optimism": {
                "0xAddress2": {
                    ZERO_ADDRESS: {
                        "threshold": "1000000000000000000",
                        "topup": "5000000000000000000",
                    }
                }
            },
        }

        result = self.service.compute_funds_status(requirements)

        # Only base should have a deficit, optimism is healthy
        assert "base" in result
        assert "optimism" not in result

    @patch.object(FundsService, "fetch_balance")
    def test_compute_funds_status_fetch_error_continues(self, mock_fetch):
        """Test that compute_funds_status continues on individual fetch errors."""
        # First call succeeds with deficit, second call fails
        mock_fetch.side_effect = [
            (100000000000000, 18),  # Low balance (deficit)
            Exception("RPC error"),  # Error on second asset
        ]

        requirements = {
            "base": {
                "0xAddress1": {
                    ZERO_ADDRESS: {
                        "threshold": "1000000000000000000",
                        "topup": "5000000000000000000",
                    },
                    "0xTokenAddress": {
                        "threshold": "1000000",
                        "topup": "10000000",
                    },
                }
            }
        }

        result = self.service.compute_funds_status(requirements)

        # Should still include the successful check's deficit
        assert "base" in result
        assert "0xAddress1" in result["base"]
        assert ZERO_ADDRESS in result["base"]["0xAddress1"]

    @patch.object(FundsService, "fetch_balance")
    def test_compute_funds_status_returns_strings(self, mock_fetch):
        """Test that deficit values are returned as strings."""
        mock_fetch.return_value = (0, 18)  # Zero balance

        requirements = {
            "base": {
                "0xAddress": {
                    ZERO_ADDRESS: {
                        "threshold": "1000",
                        "topup": "5000",
                    }
                }
            }
        }

        result = self.service.compute_funds_status(requirements)

        # Values should be strings per API spec
        assert isinstance(result["base"]["0xAddress"][ZERO_ADDRESS], str)
        assert result["base"]["0xAddress"][ZERO_ADDRESS] == "5000"


class TestFundsStatusEndpoint:
    """Tests for the /funds-status API endpoint."""

    @pytest.fixture
    async def client(self):
        """Create an async test client with mocked funds_service."""
        from main import app
        import main

        # Initialize funds_service with a mock
        main.funds_service = Mock(spec=FundsService)

        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as ac:
            yield ac

    @pytest.mark.asyncio
    async def test_funds_status_returns_empty_when_healthy(self, client):
        """Test endpoint returns {} when all balances are healthy."""
        import main

        main.funds_service.compute_funds_status.return_value = {}

        response = await client.get("/funds-status")

        assert response.status_code == 200
        assert response.json() == {}

    @pytest.mark.asyncio
    async def test_funds_status_returns_deficits(self):
        """Test endpoint returns deficits when balance is low."""
        from main import app
        import main
        from config import settings

        expected_deficits = {
            "base": {
                "0x07edA994E013AbC8619A5038455db3A6FBdd2Bca": {
                    ZERO_ADDRESS: "500000000000000"
                }
            }
        }

        # Set up mocked funds_service
        main.funds_service = Mock(spec=FundsService)
        main.funds_service.compute_funds_status.return_value = expected_deficits

        # Need to patch fund_requirements to be non-empty so the endpoint calls compute_funds_status
        mock_requirements = {
            "base": {
                "0x07edA994E013AbC8619A5038455db3A6FBdd2Bca": {
                    ZERO_ADDRESS: {"threshold": "1000", "topup": "5000"}
                }
            }
        }

        with patch.object(settings, "fund_requirements", mock_requirements):
            async with AsyncClient(
                transport=ASGITransport(app=app), base_url="http://test"
            ) as client:
                response = await client.get("/funds-status")

                assert response.status_code == 200
                assert response.json() == expected_deficits

    @pytest.mark.asyncio
    async def test_funds_status_handles_no_requirements(self):
        """Test endpoint returns {} when no requirements configured."""
        from main import app
        import main
        from config import settings

        # Set funds_service to None to test the no-requirements path
        main.funds_service = Mock(spec=FundsService)

        # Patch settings.fund_requirements to be empty
        with patch.object(settings, "fund_requirements", {}):
            async with AsyncClient(
                transport=ASGITransport(app=app), base_url="http://test"
            ) as client:
                response = await client.get("/funds-status")

                assert response.status_code == 200
                assert response.json() == {}

    @pytest.mark.asyncio
    async def test_funds_status_handles_service_error(self):
        """Test endpoint returns {} on service error."""
        from main import app
        import main
        from config import settings

        main.funds_service = Mock(spec=FundsService)
        main.funds_service.compute_funds_status.side_effect = Exception("RPC error")

        # Need to patch fund_requirements to be non-empty so the endpoint calls compute_funds_status
        mock_requirements = {
            "base": {
                "0xAddress": {
                    ZERO_ADDRESS: {"threshold": "1000", "topup": "5000"}
                }
            }
        }

        with patch.object(settings, "fund_requirements", mock_requirements):
            async with AsyncClient(
                transport=ASGITransport(app=app), base_url="http://test"
            ) as client:
                response = await client.get("/funds-status")

                assert response.status_code == 200
                # Should return empty dict on error to avoid breaking health checks
                assert response.json() == {}
