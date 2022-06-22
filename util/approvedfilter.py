# 'modX' functions modify 'X' to follow rules: only keep entries with approved basetokens
# 'assertX' functions asserts that 'X' follows the rules
#
# for all below: approved_tokens -- dict of [chainID] : list_of_approved_basetoken_addr

from copy import deepcopy

from enforce_typing import enforce_types

from util import cleancase

@enforce_types
def modTuple(approved_tokens, stakes, poolvols) -> tuple:
    return (modStakes(approved_tokens, stakes),
            modPoolvols(approved_tokens, poolvols))


@enforce_types
def modStakes(approved_tokens : dict, stakes: dict) -> dict:
    """stakes - dict of [chainID][basetoken_addr][pool_addr][LP_addr] : stake"""
    cleancase.assertApprovedTokens(approved_tokens)
    cleancase.assertStakes(stakes)
    return _modD(approved_tokens, stakes)


@enforce_types
def assertStakes(approved_tokens : dict, stakes: dict):
    """stakes - dict of [chainID][basetoken_address][pool_addr][LP_addr] : stake"""
    cleancase.assertApprovedTokens(approved_tokens)
    cleancase.assertStakes(stakes)
    _assertD(approved_tokens, stakes)


@enforce_types
def modPoolvols(approved_tokens : dict, poolvols: dict) -> dict:
    """poolvols - dict of [chainID][basetoken_address][pool_addr] : vol"""
    cleancase.assertApprovedTokens(approved_tokens)
    cleancase.assertPoolvols(poolvols)
    return _modD(approved_tokens, poolvols)


@enforce_types
def assertPoolvols(approved_tokens : dict, poolvols: dict):
    """poolvols - dict of [chainID][basetoken_address][pool_addr] : vol"""
    cleancase.assertApprovedTokens(approved_tokens)
    cleancase.assertPoolvols(poolvols)
    return _assertD(approved_tokens, poolvols)


@enforce_types
def _modD(approved_tokens : dict, D: dict) -> dict:
    """D - dict of [chainID][basetoken_addr] : abitrary_data_structure"""
    D2 = {}
    for chainID in D:
        if chainID not in approved_tokens:
            continue
        D2[chainID] = {}
        for baseaddr in D[chainID]:
            if baseaddr not in approved_tokens[chainID]:
                continue
            D2[chainID][baseaddr] = deepcopy(D[chainID][baseaddr])
                
    _assertD(approved_tokens, D2)
    return D2


@enforce_types
def _assertD(approved_tokens : dict, D: dict):
    """D - dict of [chainID][basetoken_addr] : abitrary_data_structure"""
    for chainID in D:
        assert chainID in approved_tokens
        for baseaddr in D[chainID]:
            assert baseaddr in approved_tokens[chainID]
