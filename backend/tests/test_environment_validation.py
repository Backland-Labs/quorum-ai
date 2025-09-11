"""Test environment variable validation for vote attestation system.

This test suite ensures that all required environment variables for the vote
attestation system are properly validated and that missing critical variables
are detected during startup.
"""

import os
import pytest
from unittest.mock import patch

from config import Settings


class TestEnvironmentValidation:
    """Test environment variable validation for production deployment."""

    def test_missing_openrouter_api_key_detected(self):
        """
        Test that missing OpenRouter API key is detected.
        
        This test is important because the OpenRouter API key is required for AI-powered
        voting decisions. Without it, the autonomous voting agent cannot function.
        """
        # Mock the Settings to exclude the .env file and test environment only
        with patch.dict(os.environ, {}, clear=True):
            # Override the model config to not read from .env file
            with patch.object(Settings, 'model_config', {"env_file": None, "extra": "ignore"}):
                settings = Settings()
                assert settings.openrouter_api_key is None

    def test_missing_eas_contract_address_detected(self):
        """
        Test that missing EAS contract address is detected.
        
        This test is critical because the EAS contract address is required for
        creating vote attestations on the Base network. Without it, votes cannot
        be attested on-chain.
        """
        with patch.dict(os.environ, {}, clear=True):
            settings = Settings()
            assert settings.eas_contract_address is None

    def test_missing_eas_schema_uid_detected(self):
        """
        Test that missing EAS schema UID is detected.
        
        This test ensures that the EAS schema UID (which defines the structure
        of vote attestations) is properly configured. Without it, attestations
        cannot be created with the correct format.
        """
        with patch.dict(os.environ, {}, clear=True):
            settings = Settings()
            assert settings.eas_schema_uid is None

    def test_missing_base_safe_address_detected(self):
        """
        Test that missing Base Safe address is detected.
        
        This test is important because the Base Safe address is where vote attestation
        transactions originate from. Without it, the agent cannot submit attestations.
        """
        with patch.dict(os.environ, {}, clear=True):
            settings = Settings()
            assert settings.base_safe_address is None

    def test_missing_base_rpc_endpoint_detected(self):
        """
        Test that missing Base RPC endpoint is detected.
        
        This test ensures that at least one Base network RPC endpoint is configured.
        Without it, the agent cannot connect to Base network for attestations.
        """
        with patch.dict(os.environ, {}, clear=True):
            settings = Settings()
            assert settings.get_base_rpc_endpoint() is None

    def test_celo_ledger_rpc_now_available_in_config(self):
        """
        Test that CELO_LEDGER_RPC is now properly configured in Settings.
        
        This test verifies that the previously missing CELO_LEDGER_RPC configuration
        has been added to the Settings class and works correctly.
        """
        with patch.dict(os.environ, {"CELO_LEDGER_RPC": "https://forno.celo.org"}):
            settings = Settings()
            # This should now work because celo_ledger_rpc is defined in Settings
            assert settings.celo_ledger_rpc == "https://forno.celo.org"

    def test_complete_eas_configuration_valid(self):
        """
        Test that complete EAS configuration is properly loaded.
        
        This test verifies that when all required EAS environment variables are
        provided, they are correctly loaded into the Settings object.
        """
        eas_config = {
            "OPENROUTER_API_KEY": "test_openrouter_key",
            "EAS_CONTRACT_ADDRESS": "0x4200000000000000000000000000000000000021",
            "EAS_SCHEMA_UID": "0x1234567890abcdef1234567890abcdef1234567890abcdef1234567890abcdef",
            "BASE_SAFE_ADDRESS": "0x9876543210fedcba9876543210fedcba98765432",
            "BASE_RPC_URL": "https://mainnet.base.org"
        }
        
        with patch.dict(os.environ, eas_config):
            settings = Settings()
            assert settings.openrouter_api_key == "test_openrouter_key"
            assert settings.eas_contract_address == "0x4200000000000000000000000000000000000021"
            assert settings.eas_schema_uid == "0x1234567890abcdef1234567890abcdef1234567890abcdef1234567890abcdef"
            assert settings.base_safe_address == "0x9876543210fedcba9876543210fedcba98765432"
            assert settings.get_base_rpc_endpoint() == "https://mainnet.base.org"

    def test_base_rpc_endpoint_priority(self):
        """
        Test that base_rpc_url takes priority over base_ledger_rpc.
        
        This test ensures that the get_base_rpc_endpoint() method correctly
        prioritizes base_rpc_url when both RPC endpoint variables are set.
        """
        config = {
            "BASE_RPC_URL": "https://base-url-priority.com",
            "BASE_LEDGER_RPC": "https://base-ledger-secondary.com"
        }
        
        with patch.dict(os.environ, config):
            settings = Settings()
            assert settings.get_base_rpc_endpoint() == "https://base-url-priority.com"

    def test_startup_environment_validation_fails_for_missing_critical_vars(self):
        """
        Test that startup validation fails when critical environment variables are missing.
        
        This test verifies that the startup validation function properly detects
        missing critical environment variables for the attestation system.
        """
        with patch.dict(os.environ, {}, clear=True):
            # Override the model config to not read from .env file
            with patch.object(Settings, 'model_config', {"env_file": None, "extra": "ignore"}):
                settings = Settings()
                
                # This should fail because required environment variables are missing
                with pytest.raises(ValueError) as exc_info:
                    settings.validate_attestation_environment()
                
                # Verify the error message mentions the missing variables
                assert "Missing required environment variables" in str(exc_info.value)
                assert "OPENROUTER_API_KEY" in str(exc_info.value)
                assert "EAS_CONTRACT_ADDRESS" in str(exc_info.value)
                assert "BASE_SAFE_ADDRESS or SAFE_CONTRACT_ADDRESSES with 'base' key" in str(exc_info.value)

    def test_startup_environment_validation_passes_for_complete_config(self):
        """
        Test that startup validation passes when all required variables are present.
        
        This test verifies that the startup validation function correctly validates
        a complete attestation environment configuration.
        """
        complete_config = {
            "OPENROUTER_API_KEY": "test_key",
            "EAS_CONTRACT_ADDRESS": "0x4200000000000000000000000000000000000021",
            "EAS_SCHEMA_UID": "0x1234567890abcdef1234567890abcdef1234567890abcdef1234567890abcdef",
            "BASE_SAFE_ADDRESS": "0x9876543210fedcba9876543210fedcba98765432",
            "BASE_RPC_URL": "https://mainnet.base.org"
        }
        
        with patch.dict(os.environ, complete_config):
            settings = Settings()
            
            # This should now pass because all required environment variables are present
            result = settings.validate_attestation_environment()
            assert result is True

    def test_validation_fails_for_invalid_eas_contract_address(self):
        """
        Test that validation fails for invalid EAS contract address format.
        
        This test ensures that the validation function properly checks the format
        of the EAS contract address and rejects invalid formats.
        """
        invalid_config = {
            "OPENROUTER_API_KEY": "test_key",
            "EAS_CONTRACT_ADDRESS": "invalid_address_without_0x",  # Invalid format
            "EAS_SCHEMA_UID": "0x1234567890abcdef1234567890abcdef1234567890abcdef1234567890abcdef",
            "BASE_SAFE_ADDRESS": "0x9876543210fedcba9876543210fedcba98765432",
            "BASE_RPC_URL": "https://mainnet.base.org"
        }
        
        with patch.dict(os.environ, invalid_config):
            settings = Settings()
            
            with pytest.raises(ValueError) as exc_info:
                settings.validate_attestation_environment()
            
            assert "Invalid EAS_CONTRACT_ADDRESS format" in str(exc_info.value)

    def test_validation_fails_for_invalid_eas_schema_uid(self):
        """
        Test that validation fails for invalid EAS schema UID format.
        
        This test ensures that the validation function properly checks the format
        of the EAS schema UID (must be 32-byte hex string with 0x prefix).
        """
        invalid_config = {
            "OPENROUTER_API_KEY": "test_key",
            "EAS_CONTRACT_ADDRESS": "0x4200000000000000000000000000000000000021",
            "EAS_SCHEMA_UID": "0x123",  # Too short, invalid format
            "BASE_SAFE_ADDRESS": "0x9876543210fedcba9876543210fedcba98765432",
            "BASE_RPC_URL": "https://mainnet.base.org"
        }
        
        with patch.dict(os.environ, invalid_config):
            settings = Settings()
            
            with pytest.raises(ValueError) as exc_info:
                settings.validate_attestation_environment()
            
            assert "Invalid EAS_SCHEMA_UID format" in str(exc_info.value)

    def test_validation_fails_for_invalid_base_safe_address(self):
        """
        Test that validation fails for invalid Base Safe address format.
        
        This test ensures that the validation function properly checks the format
        of the Base Safe address.
        """
        invalid_config = {
            "OPENROUTER_API_KEY": "test_key", 
            "EAS_CONTRACT_ADDRESS": "0x4200000000000000000000000000000000000021",
            "EAS_SCHEMA_UID": "0x1234567890abcdef1234567890abcdef1234567890abcdef1234567890abcdef",
            "BASE_SAFE_ADDRESS": "invalid_safe_address",  # Invalid format
            "BASE_RPC_URL": "https://mainnet.base.org"
        }
        
        with patch.dict(os.environ, invalid_config):
            settings = Settings()
            
            with pytest.raises(ValueError) as exc_info:
                settings.validate_attestation_environment()
            
            assert "Invalid BASE_SAFE_ADDRESS format" in str(exc_info.value)

    def test_validation_fails_when_safe_contract_addresses_missing_base_key(self):
        """
        Test that validation fails when SAFE_CONTRACT_ADDRESSES is configured but missing 'base' key.
        
        This test verifies that the new validation logic properly detects when 
        SAFE_CONTRACT_ADDRESSES is provided but doesn't contain the required 'base' key.
        """
        config = {
            "OPENROUTER_API_KEY": "test_key",
            "EAS_CONTRACT_ADDRESS": "0x4200000000000000000000000000000000000021",
            "EAS_SCHEMA_UID": "0x1234567890abcdef1234567890abcdef1234567890abcdef1234567890abcdef",
            "SAFE_CONTRACT_ADDRESSES": '{"gnosis": "0x456", "ethereum": "0x789"}',  # Missing 'base' key
            "BASE_RPC_URL": "https://mainnet.base.org"
        }
        
        with patch.dict(os.environ, config):
            settings = Settings()
            
            with pytest.raises(ValueError) as exc_info:
                settings.validate_attestation_environment()
            
            assert "SAFE_CONTRACT_ADDRESSES must contain 'base' key" in str(exc_info.value)

    def test_validation_passes_with_safe_contract_addresses_containing_base_key(self):
        """
        Test that validation passes when SAFE_CONTRACT_ADDRESSES contains 'base' key.
        
        This test verifies that the new auto-assignment logic works correctly and
        validation passes when the 'base' key is present in SAFE_CONTRACT_ADDRESSES.
        """
        config = {
            "OPENROUTER_API_KEY": "test_key",
            "EAS_CONTRACT_ADDRESS": "0x4200000000000000000000000000000000000021",
            "EAS_SCHEMA_UID": "0x1234567890abcdef1234567890abcdef1234567890abcdef1234567890abcdef",
            "SAFE_CONTRACT_ADDRESSES": '{"base": "0x07edA994E013AbC8619A5038455db3A6FBdd2Bca", "gnosis": "0x456"}',
            "BASE_RPC_URL": "https://mainnet.base.org"
        }
        
        with patch.dict(os.environ, config):
            settings = Settings()
            
            # Should auto-assign base_safe_address from 'base' key
            assert settings.base_safe_address == "0x07edA994E013AbC8619A5038455db3A6FBdd2Bca"
            
            # Validation should pass
            result = settings.validate_attestation_environment()
            assert result is True