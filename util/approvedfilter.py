# 'modX' functions modify 'X' to follow rules: only keep entries with approved basetokens
# 'assertX' functions asserts that 'X' follows the rules

from copy import deepcopy


def modTuple(approved_tokens, stakes, poolvols, rates) -> tuple:
    return (modStakes(approved_tokens, stakes),
            modPoolvols(approved_tokens, poolvols),
            modRates(approved_tokens, rates))


def modStakes(approved_tokens, stakes: dict) -> dict:
    """
    @arguments
      approved_tokens -- list of (chainID, approved_basetoken_addr)
      stakes - dict of [chainID][basetoken_addr][pool_addr][LP_addr] : stake
    """
    stakes2 = {}
    for chainID in stakes:
        stakes2[chainID] = {}
        for baseaddr in stakes[chainID]:
            if (chainID, baseaddr) in approved_tokens:
                stakes2[chainID][baseaddr] = deepcopy(stakes[chainID][baseaddr])
                
    assertStakes(approved_tokens, stakes2)
    return stakes2


def assertStakes(approved_tokens, stakes: dict):
    """
    @arguments
      approved_tokens -- list of (chainID, approved_basetoken_addr)
      stakes - dict of [chainID][basetoken_address][pool_addr][LP_addr] : stake
    """
    for chainID in stakes:
        for baseaddr in stakes[chainID]:
            assert (chainID, baseaddr) in approved_tokens


def modPoolvols(approved_tokens, poolvols: dict) -> dict:
    """
    @arguments
      approved_tokens -- list of (chainID, approved_basetoken_addr)
      poolvols - dict of [chainID][basetoken_address][pool_addr] : vol
    """
    poolvols2: dict = {}
    for chainID in poolvols:
        poolvols2[chainID] = {}
        for baseaddr in poolvols[chainID]:
            if (chainID, baseaddr) in approved_tokens:
                poolvols2[chainID][baseaddr] = deepcopy(poolvols[chainID][baseaddr])

    assertPoolvols(poolvols2)
    return poolvols2


def assertPoolvols(approved_tokens, poolvols: dict):
    """
    @arguments
      approved_tokens -- list of (chainID, approved_basetoken_addr)
      poolvols - dict of [chainID][basetoken_address][pool_addr] : vol
    """
    for chainID in poolvols:
        for baseaddr in poolvols[chainID]:
            assert (chainID, baseaddr) in approved_tokens
