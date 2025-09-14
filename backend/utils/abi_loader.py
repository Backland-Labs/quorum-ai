"""ABI Loader for On-Chain Contract Interfaces.

This utility loads Application Binary Interface (ABI) definitions for various
smart contracts including governor contracts, EAS, and AttestationTracker.
These ABIs are essential for encoding and decoding transaction data when
interacting with smart contracts.

Used for:
- Governor contracts (Compound Bravo, OpenZeppelin Governor, etc.)
- Ethereum Attestation Service (EAS) integration
- AttestationTracker wrapper contract
"""

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
            with open(abi_path, "r") as f:
                data = json.load(f)

            # Handle both formats:
            # 1. Direct ABI array (e.g., attestation_tracker.json)
            # 2. Object with "abi" field (e.g., eas.json, eip712proxy.json)
            if isinstance(data, list):
                abi = data
            elif isinstance(data, dict) and "abi" in data:
                abi = data["abi"]
                if not isinstance(abi, list):
                    raise ABILoaderError(
                        f"Invalid ABI format for '{name}': 'abi' field is not a list"
                    )
            else:
                raise ABILoaderError(
                    f"Invalid ABI format for '{name}': expected list or object with 'abi' field"
                )

            return abi
        except json.JSONDecodeError as e:
            raise ABILoaderError(f"Invalid JSON in ABI '{name}': {e}")
        except Exception as e:
            raise ABILoaderError(f"Error loading ABI '{name}': {e}")


# Global instance for standalone function
_loader = ABILoader()


def load_abi(name: str) -> List[Dict[str, Any]]:
    """Load ABI by name using global loader instance.

    Args:
        name: The ABI name (e.g., 'eas', 'attestation_tracker')

    Returns:
        ABI as list of dictionaries

    Raises:
        ABILoaderError: If ABI not found or invalid
    """
    return _loader.load(name)
