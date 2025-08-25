"""ABI Loader for On-Chain Governor Contract Interfaces.

NOTE: This module is currently not in active use as the system has migrated to
Snapshot (off-chain) voting. However, this code is being retained for future
implementation of on-chain governance support.

This utility loads Application Binary Interface (ABI) definitions for various
on-chain governor contracts. These ABIs are essential for encoding and decoding
transaction data when interacting with governor smart contracts.

Future work will use this loader when constructing on-chain vote transactions
for governor contracts like Compound Bravo, OpenZeppelin Governor, etc.
"""

import json
from functools import lru_cache
from pathlib import Path
from typing import Any


class ABILoaderError(Exception):
    pass


class ABILoader:
    def __init__(self) -> None:
        self.abi_dir = Path(__file__).resolve().parent.parent / "abi"

    @lru_cache(maxsize=32)
    def load(self, name: str) -> list[dict[str, Any]]:
        abi_path = self.abi_dir / f"{name}.json"

        if not abi_path.exists():
            msg = f"ABI '{name}' not found"
            raise ABILoaderError(msg)

        try:
            with open(abi_path) as f:
                abi = json.load(f)

            if not isinstance(abi, list):
                msg = f"Invalid ABI format for '{name}': expected list"
                raise ABILoaderError(msg)

            return abi
        except json.JSONDecodeError as e:
            msg = f"Invalid JSON in ABI '{name}': {e}"
            raise ABILoaderError(msg)
        except Exception as e:
            msg = f"Error loading ABI '{name}': {e}"
            raise ABILoaderError(msg)
