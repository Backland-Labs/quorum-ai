import pytest
from backend.services.governor_registry import (
    GovernorType, 
    GovernorMeta, 
    get_governor, 
    GovernorRegistryError,
    GOVERNORS
)


class TestGovernorType:
    def test_governor_type_enum_values(self):
        assert GovernorType.COMPOUND_BRAVO == "compound_bravo"
        assert GovernorType.NOUNS == "nouns"
        assert GovernorType.UNISWAP_OZ == "uniswap_oz"
        assert GovernorType.ARBITRUM == "arbitrum"


class TestGovernorMeta:
    def test_valid_governor_meta(self):
        meta = GovernorMeta(
            id="compound-mainnet",
            chain_id=1,
            address="0xc0Da02939E1441F497fd74F78cE7Decb17B66529",
            type=GovernorType.COMPOUND_BRAVO
        )
        
        assert meta.id == "compound-mainnet"
        assert meta.chain_id == 1
        assert meta.address == "0xc0Da02939E1441F497fd74F78cE7Decb17B66529"
        assert meta.type == GovernorType.COMPOUND_BRAVO

    def test_invalid_id_format(self):
        with pytest.raises(ValueError):
            GovernorMeta(
                id="Invalid_ID!",
                chain_id=1,
                address="0xc0Da02939E1441F497fd74F78cE7Decb17B66529",
                type=GovernorType.COMPOUND_BRAVO
            )

    def test_address_checksum_validation(self):
        meta = GovernorMeta(
            id="test-governor",
            chain_id=1,
            address="0xc0da02939e1441f497fd74f78ce7decb17b66529",
            type=GovernorType.COMPOUND_BRAVO
        )
        
        assert meta.address == "0xc0Da02939E1441F497fd74F78cE7Decb17B66529"

    def test_invalid_address_format(self):
        with pytest.raises(ValueError):
            GovernorMeta(
                id="test-governor",
                chain_id=1,
                address="invalid-address",
                type=GovernorType.COMPOUND_BRAVO
            )


class TestGovernorRegistry:
    def test_registry_contains_expected_governors(self):
        expected_governors = [
            "compound-mainnet",
            "compound-sepolia", 
            "nouns-mainnet",
            "uniswap-mainnet",
            "arbitrum-mainnet"
        ]
        
        for gov_id in expected_governors:
            assert gov_id in GOVERNORS

    def test_get_existing_governor(self):
        meta, abi = get_governor("compound-mainnet")
        
        assert isinstance(meta, GovernorMeta)
        assert meta.id == "compound-mainnet"
        assert meta.chain_id == 1
        assert meta.type == GovernorType.COMPOUND_BRAVO
        
        assert isinstance(abi, list)
        assert len(abi) > 0

    def test_get_nonexistent_governor(self):
        with pytest.raises(GovernorRegistryError, match="Governor 'nonexistent' not found"):
            get_governor("nonexistent")

    def test_all_registered_governors_have_valid_abis(self):
        for gov_id in GOVERNORS.keys():
            meta, abi = get_governor(gov_id)
            
            assert isinstance(meta, GovernorMeta)
            assert isinstance(abi, list)
            assert len(abi) > 0
            
            function_names = [func["name"] for func in abi if func["type"] == "function"]
            assert "castVote" in function_names

    def test_mainnet_and_testnet_coverage(self):
        mainnet_governors = [gov for gov in GOVERNORS.values() if gov.chain_id == 1]
        testnet_governors = [gov for gov in GOVERNORS.values() if gov.chain_id == 11155111]
        
        assert len(mainnet_governors) >= 4
        assert len(testnet_governors) >= 1

    def test_governor_addresses_are_checksummed(self):
        for meta in GOVERNORS.values():
            assert meta.address[0:2] == "0x"
            assert len(meta.address) == 42
            assert any(c.isupper() for c in meta.address[2:])
