from functools import lru_cache
from pathlib import Path
import json
from typing import List, Dict, Any


class ABILoaderError(Exception):
    pass


class ABILoader:
    def __init__(self) -> None:
        self.abi_dir = Path(__file__).resolve().parent.parent / "abi"

    @lru_cache(maxsize=32)
    def load(self, name: str) -> List[Dict[str, Any]]:
        abi_path = self.abi_dir / f"{name}.json"
        
        if not abi_path.exists():
            raise ABILoaderError(f"ABI '{name}' not found")
        
        try:
            with open(abi_path, 'r') as f:
                abi = json.load(f)
            
            if not isinstance(abi, list):
                raise ABILoaderError(f"Invalid ABI format for '{name}': expected list")
            
            return abi
        except json.JSONDecodeError as e:
            raise ABILoaderError(f"Invalid JSON in ABI '{name}': {e}")
        except Exception as e:
            raise ABILoaderError(f"Error loading ABI '{name}': {e}")
