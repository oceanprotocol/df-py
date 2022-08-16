# 'modX' functions modify 'X' to follow rules: only keep entries with approved basetokens
# 'assertX' functions asserts that 'X' follows the rules

from copy import deepcopy
from typing import Dict, List, Tuple

from enforce_typing import enforce_types

from util import cleancase


@enforce_types
def modTuple(approved_token_addrs, stakes, poolvols) -> Tuple[dict, dict]:
    return (
        modStakes(approved_token_addrs, stakes),
        modPoolvols(approved_token_addrs, poolvols),
    )


@enforce_types
def modStakes(approved_token_addrs: dict, stakes: dict) -> dict:
    """stakes - dict of [chainID][basetoken_addr][pool_addr][LP_addr] : stake"""
    cleancase.asserAllocations(stakes)
    return _modD(approved_token_addrs, stakes)


@enforce_types
def assertStakes(approved_token_addrs: dict, stakes: dict):
    """stakes - dict of [chainID][basetoken_address][pool_addr][LP_addr] : stake"""
    cleancase.asserAllocations(stakes)
    _assertD(approved_token_addrs, stakes)


@enforce_types
def modPoolvols(approved_token_addrs: dict, poolvols: dict) -> dict:
    """poolvols - dict of [chainID][basetoken_address][pool_addr] : vol"""
    cleancase.assertNFTvols(poolvols)
    return _modD(approved_token_addrs, poolvols)


@enforce_types
def assertPoolvols(approved_token_addrs: dict, poolvols: dict):
    """poolvols - dict of [chainID][basetoken_address][pool_addr] : vol"""
    cleancase.assertNFTvols(poolvols)
    return _assertD(approved_token_addrs, poolvols)


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
