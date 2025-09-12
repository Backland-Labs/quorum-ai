import pytest
import json
from pathlib import Path
from backend.utils.abi_loader import ABILoader, ABILoaderError


class TestABILoader:
    def test_load_existing_abi(self):
        loader = ABILoader()
        abi = loader.load("compound_bravo")
        
        assert isinstance(abi, list)
        assert len(abi) > 0
        
        function_names = [func["name"] for func in abi if func["type"] == "function"]
        assert "castVote" in function_names
        assert "castVoteWithReason" in function_names
        assert "state" in function_names
        assert "hasVoted" in function_names
        assert "proposalVotes" in function_names

    def test_load_nonexistent_abi(self):
        loader = ABILoader()
        
        with pytest.raises(ABILoaderError, match="ABI 'nonexistent' not found"):
            loader.load("nonexistent")

    def test_caching_behavior(self):
        loader = ABILoader()
        
        abi1 = loader.load("compound_bravo")
        abi2 = loader.load("compound_bravo")
        
        assert abi1 is abi2


    def test_abi_structure_validation(self):
        loader = ABILoader()
        abi = loader.load("compound_bravo")
        
        for item in abi:
            assert "type" in item
            if item["type"] == "function":
                assert "name" in item
                assert "inputs" in item
                assert "outputs" in item
                assert "stateMutability" in item

    def test_cast_vote_function_signature(self):
        loader = ABILoader()
        abi = loader.load("compound_bravo")
        
        cast_vote = next(func for func in abi if func.get("name") == "castVote")
        
        assert len(cast_vote["inputs"]) == 2
        assert cast_vote["inputs"][0]["type"] == "uint256"
        assert cast_vote["inputs"][1]["type"] == "uint8"
        assert cast_vote["stateMutability"] == "nonpayable"

    def test_cast_vote_with_reason_function_signature(self):
        loader = ABILoader()
        abi = loader.load("compound_bravo")
        
        cast_vote_with_reason = next(func for func in abi if func.get("name") == "castVoteWithReason")
        
        assert len(cast_vote_with_reason["inputs"]) == 3
        assert cast_vote_with_reason["inputs"][0]["type"] == "uint256"
        assert cast_vote_with_reason["inputs"][1]["type"] == "uint8"
        assert cast_vote_with_reason["inputs"][2]["type"] == "string"
        assert cast_vote_with_reason["stateMutability"] == "nonpayable"

    def test_invalid_json_format(self, tmp_path):
        from pathlib import Path
        
        invalid_abi_dir = tmp_path / "invalid_abi"
        invalid_abi_dir.mkdir()
        
        invalid_file = invalid_abi_dir / "invalid.json"
        invalid_file.write_text("{ invalid json")
        
        loader = ABILoader()
        loader.abi_dir = invalid_abi_dir
        
        with pytest.raises(ABILoaderError, match="Invalid JSON"):
            loader.load("invalid")

    def test_non_list_abi_format(self, tmp_path):
        from pathlib import Path
        import json
        
        invalid_abi_dir = tmp_path / "invalid_abi"
        invalid_abi_dir.mkdir()
        
        invalid_file = invalid_abi_dir / "notlist.json"
        invalid_file.write_text(json.dumps({"not": "a list"}))
        
        loader = ABILoader()
        loader.abi_dir = invalid_abi_dir
        
        with pytest.raises(ABILoaderError, match="Invalid ABI format"):
            loader.load("notlist")
