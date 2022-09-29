# 'modX' functions modify 'X' to follow rules: only keep entries with approved basetokens
# 'assertX' functions asserts that 'X' follows the rules

from typing import Tuple

from enforce_typing import enforce_types

from util import cleancase


@enforce_types
def modTuple(allocations, nftvols) -> Tuple[dict, dict]:
    return (
        modAllocations(allocations),
        modNFTvols(nftvols),
    )


@enforce_types
def modAllocations(allocations: dict) -> dict:
    """allocations - dict of [chainID][basetoken_addr][NFT_addr] : percentage"""
    cleancase.assertAllocations(allocations)
    return allocations


@enforce_types
def assertAllocations(allocations: dict):
    """stakes - dict of [chainID][basetoken_address][NFT_addr][LP_addr] : stake"""
    cleancase.assertAllocations(allocations)


@enforce_types
def modNFTvols(nftvols: dict) -> dict:
    """nftvols - dict of [chainID][basetoken_address][NFT_addr] : vol"""
    cleancase.assertNFTvols(nftvols)
    return nftvols


@enforce_types
def assertNFTvols(nftvols: dict):
    """nftvols - dict of [chainID][basetoken_address][NFT_addr] : vol"""
    cleancase.assertNFTvols(nftvols)
    return nftvols
