# 'modX' functions modify 'X' to follow rules: only keep entries with approved basetokens
# 'assertX' functions asserts that 'X' follows the rules

from copy import deepcopy
from typing import Dict, List, Tuple

from enforce_typing import enforce_types

from util import cleancase


@enforce_types
def modTuple(approved_token_addrs, allocations, nftvols) -> Tuple[dict, dict]:
    return (
        modAllocations(allocations),
        modNFTvols(approved_token_addrs, nftvols),
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
def modNFTvols(approved_token_addrs: dict, nftvols: dict) -> dict:
    """nftvols - dict of [chainID][basetoken_address][NFT_addr] : vol"""
    cleancase.assertNFTvols(nftvols)
    return _modD(approved_token_addrs, nftvols)


@enforce_types
def assertNFTvols(approved_token_addrs: dict, nftvols: dict):
    """nftvols - dict of [chainID][basetoken_address][NFT_addr] : vol"""
    cleancase.assertNFTvols(nftvols)
    return _assertD(approved_token_addrs, nftvols)


@enforce_types
def _modD(approved_token_addrs: Dict[int, List[str]], D: dict) -> dict:
    """
    @description
      Filter out entries that aren't in approved_token_addrs

    @arguments
      approved_token_addrs - dict of [chainID] : list_of_addr
      D - dict of [chainID][basetoken_addr] : abitrary_data_structure
    """
    D2: dict = {}
    for chainID in D:
        if chainID not in approved_token_addrs:
            continue
        D2[chainID] = {}
        for basetoken_addr in D[chainID]:
            if basetoken_addr not in approved_token_addrs[chainID]:
                print(basetoken_addr)
                continue
            D2[chainID][basetoken_addr] = deepcopy(D[chainID][basetoken_addr])

    _assertD(approved_token_addrs, D2)
    return D2


@enforce_types
def _assertD(approved_token_addrs: Dict[int, List[str]], D: dict):
    """D - dict of [chainID][basetoken_addr] : abitrary_data_structure"""
    for chainID in D:
        assert chainID in approved_token_addrs
        for basetoken_addr in D[chainID]:
            assert basetoken_addr in approved_token_addrs[chainID]
