
def modStakes(stakes: dict) -> dict:
    """
    Make addresses lowercase, and token symbols uppercase
      stakes - dict of [chainID][basetoken_symbol][pool_addr][LP_addr] : stake
    """
    stakes2 = {}
    for chainID in stakes:
        chainID2 = chainID
        stakes2[chainID2] = {}
        for basetoken in stakes[chainID]:
            basetoken2 = basetoken.upper()
            stakes2[chainID2][basetoken2] = {}
            for pool_addr in stakes[chainID][basetoken]:
                pool_addr2 = pool_addr.lower()
                stakes2[chainID2][basetoken2][pool_addr2] = {}
                for LP_addr,st in stakes[chainID][basetoken][pool_addr].items():
                    LP_addr2 = LP_addr.lower()
                    stakes2[chainID2][basetoken2][pool_addr2][LP_addr2] = st

    assertStakes(stakes2)
                    
    return stakes2

def assertStakes(stakes: dict):
    """assert that upper/lowercase rules are followed"""
    for chainID in stakes:
        for basetoken in stakes[chainID]:
            assert basetoken == basetoken.upper()
            for pool_addr in stakes[chainID][basetoken]:
                assert pool_addr == pool_addr.lower()
                for LP_addr in stakes[chainID][basetoken][pool_addr]:
                    assert LP_addr == LP_addr.lower()
                                             
                
def modPoolvols(poolvols: dict) -> dict:
    """
    Make addresses lowercase, and token symbols uppercase
      poolvols - dict of [chainID][basetoken_symbol][pool_addr] : vol
    """
    poolvols2 = {}
    for chainID in poolvols:
        chainID2 = chainID
        poolvols2[chainID2] = {}
        for basetoken in poolvols[chainID]:
            basetoken2 = basetoken.upper()
            poolvols2[chainID2][basetoken2] = {}
            for pool_addr, vol in poolvols[chainID][basetoken].items():
                pool_addr2 = pool_addr.lower()
                poolvols2[chainID2][basetoken2][pool_addr2] = vol

    assertPoolvols(poolvols2)
                
    return poolvols2


def assertPoolvols(poolvols: dict):
    """assert that upper/lowercase rules are followed"""
    poolvols2 = {}
    for chainID in poolvols:
        for basetoken in poolvols[chainID]:
            assert basetoken == basetoken.upper()
            for pool_addr in poolvols[chainID][basetoken]:
                assert pool_addr == pool_addr.lower()


def modRates(rates: dict) -> dict:
    """
    Make addresses lowercase, and token symbols uppercase
      rates - dict of [basetoken_symbol] : USD_per_basetoken
    """
    rates2 = {}
    for basetoken, rate in rates.items():
        basetoken2 = basetoken.upper()
        rates2[basetoken2] = rate

    assertRates(rates2)
                
    return rates2


def assertRates(rates: dict):
    """assert that upper/lowercase rules are followed"""
    for basetoken in rates:
        assert basetoken == basetoken.upper()
