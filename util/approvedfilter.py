# 'modX' functions modify 'X' to follow rules: only keep entries with approved basetokens
# 'assertX' functions asserts that 'X' follows the rules

from copy import deepcopy

from enforce_typing import enforce_types

from util import cleancase
from util.tok import TokSet

@enforce_types
def modTuple(approved_tokens, stakes, poolvols) -> tuple:
    return (modStakes(approved_tokens, stakes),
            modPoolvols(approved_tokens, poolvols))


@enforce_types
def modStakes(approved_tokens : TokSet, stakes: dict) -> dict:
    """stakes - dict of [chainID][basetoken_addr][pool_addr][LP_addr] : stake"""
    cleancase.assertStakes(stakes)
    return _modD(approved_tokens, stakes)


@enforce_types
def assertStakes(approved_tokens : TokSet, stakes: dict):
    """stakes - dict of [chainID][basetoken_address][pool_addr][LP_addr] : stake"""
    cleancase.assertStakes(stakes)
    _assertD(approved_tokens, stakes)


@enforce_types
def modPoolvols(approved_tokens : TokSet, poolvols: dict) -> dict:
    """poolvols - dict of [chainID][basetoken_address][pool_addr] : vol"""
    cleancase.assertPoolvols(poolvols)
    return _modD(approved_tokens, poolvols)


@enforce_types
def assertPoolvols(approved_tokens : TokSet, poolvols: dict):
    """poolvols - dict of [chainID][basetoken_address][pool_addr] : vol"""
    cleancase.assertPoolvols(poolvols)
    return _assertD(approved_tokens, poolvols)


@enforce_types
def _modD(approved_tokens : TokSet, D: dict) -> dict:
    """
    @description
      Filter out entries that aren't in approved_tokens

    @arguments
      approved_tokens - TokSet 
      D - dict of [chainID][basetoken_addr] : abitrary_data_structure
    """
    D2: dict = {}
    for chainID in D:
        if not approved_tokens.hasChain(chainID):
            continue
        D2[chainID] = {}
        for baseaddr in D[chainID]:
            if not approved_tokens.hasAddress(chainID, baseaddr):
                continue
            D2[chainID][baseaddr] = deepcopy(D[chainID][baseaddr])
                
    _assertD(approved_tokens, D2)
    return D2


@enforce_types
def _assertD(approved_tokens : TokSet, D: dict):
    """D - dict of [chainID][basetoken_addr] : abitrary_data_structure"""
    for chainID in D:
        assert approved_tokens.hasChain(chainID)
        for baseaddr in D[chainID]:
            assert approved_tokens.hasAddress(chainID, baseaddr)
