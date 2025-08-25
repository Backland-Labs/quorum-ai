"""Governor Registry for On-Chain Voting Support.

NOTE: This module is currently not in active use as the system has migrated to
Snapshot (off-chain) voting. However, this code is being retained for future
implementation of on-chain governance support.

This registry contains definitions and utilities for interacting with various
on-chain governor contracts including:
- Compound Governor Bravo
- Nouns DAO Governor
- Uniswap Governor (OpenZeppelin based)
- Arbitrum Governor

Future work will integrate this with the agent voting system to support both
Snapshot (off-chain) and traditional governor (on-chain) voting mechanisms.
"""

from enum import Enum
from typing import Any

from pydantic import BaseModel, Field, field_validator
from web3 import Web3

from utils.abi_loader import ABILoader


class GovernorRegistryError(Exception):
    pass


class GovernorType(str, Enum):
    COMPOUND_BRAVO = "compound_bravo"
    NOUNS = "nouns"
    UNISWAP_OZ = "uniswap_oz"
    ARBITRUM = "arbitrum"


class GovernorMeta(BaseModel):
    id: str = Field(pattern=r"^[a-z0-9\-]+$")
    chain_id: int
    address: str
    type: GovernorType

    @field_validator("address")
    @classmethod
    def checksum_address(cls, v: str) -> str:
        try:
            return Web3.to_checksum_address(v)
        except ValueError as e:
            msg = f"Invalid Ethereum address: {e}"
            raise ValueError(msg)


GOVERNORS: dict[str, GovernorMeta] = {
    "compound-mainnet": GovernorMeta(
        id="compound-mainnet",
        chain_id=1,
        address="0xc0Da02939E1441F497fd74F78cE7Decb17B66529",
        type=GovernorType.COMPOUND_BRAVO,
    ),
    "compound-sepolia": GovernorMeta(
        id="compound-sepolia",
        chain_id=11155111,
        address="0xAbCdEf1234567890123456789012345678901234",
        type=GovernorType.COMPOUND_BRAVO,
    ),
    "nouns-mainnet": GovernorMeta(
        id="nouns-mainnet",
        chain_id=1,
        address="0x6f3E6272A167e8AcCb32072d08E0957F9c79223d",
        type=GovernorType.NOUNS,
    ),
    "uniswap-mainnet": GovernorMeta(
        id="uniswap-mainnet",
        chain_id=1,
        address="0x408ED6354d4973f66138C91495F2f2FCbd8724C3",
        type=GovernorType.UNISWAP_OZ,
    ),
    "arbitrum-mainnet": GovernorMeta(
        id="arbitrum-mainnet",
        chain_id=1,
        address="0xf07DeD9dC292157749B6Fd268E37DF6EA38395B9",
        type=GovernorType.ARBITRUM,
    ),
}


def get_governor(governor_id: str) -> tuple[GovernorMeta, list[dict[str, Any]]]:
    if governor_id not in GOVERNORS:
        msg = f"Governor '{governor_id}' not found"
        raise GovernorRegistryError(msg)

    meta = GOVERNORS[governor_id]
    abi_loader = ABILoader()
    abi = abi_loader.load(meta.type.value)

    return meta, abi
