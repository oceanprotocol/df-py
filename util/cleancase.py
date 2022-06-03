# 'modX' functions modify 'X' to follow rules: lowercase address,uppercase token
# 'assertX' functions asserts that 'X' follows the rules

FAKE_CHAINID = 99
FAKE_TOKEN = "fake_token"


def modStakes(stakes: dict) -> dict:
    """stakes - dict of [chainID][basetoken_address][pool_addr][LP_addr] : stake"""
    stakes2: dict = {}
    for chainID in stakes:
        chainID2 = chainID
        stakes2[chainID2] = {}
        for baseaddr in stakes[chainID]:
            baseaddr2 = baseaddr.lower()
            stakes2[chainID2][baseaddr2] = {}
            for pool_addr in stakes[chainID][baseaddr]:
                pool_addr2 = pool_addr.lower()
                stakes2[chainID2][baseaddr2][pool_addr2] = {}
                for LP_addr, st in stakes[chainID][baseaddr][pool_addr].items():
                    LP_addr2 = LP_addr.lower()
                    stakes2[chainID2][baseaddr2][pool_addr2][LP_addr2] = st

    assertStakes(stakes2)
    return stakes2


def assertStakes(stakes: dict):
    """stakes - dict of [chainID][basetoken_address][pool_addr][LP_addr] : stake"""
    for chainID in stakes:
        for basetoken in stakes[chainID]:
            print("b", basetoken, basetoken.lower())
            assert basetoken == basetoken.lower(), basetoken
            for pool_addr in stakes[chainID][basetoken]:
                assert pool_addr == pool_addr.lower(), pool_addr
                for LP_addr in stakes[chainID][basetoken][pool_addr]:
                    assert LP_addr == LP_addr.lower(), LP_addr


def assertStakesUsd(stakes_USD: dict):
    """stakes_USD - dict of [chainID][pool_addr][LP_addr] : stake"""
    for chainID in stakes_USD:
        assertStakesUsdAtChain(stakes_USD[chainID])


def assertStakesAtChain(stakes_at_chain: dict):
    """stakes_at_chain - dict of [basetoken_address][pool_addr][LP_addr] : stake"""
    assertStakes({FAKE_CHAINID: stakes_at_chain})


def assertStakesUsdAtChain(stakes_at_chain: dict):
    """stakes_USD_at_chain - dict of [pool_addr][LP_addr] : stake"""
    assertStakes({FAKE_CHAINID: {FAKE_TOKEN: stakes_at_chain}})


def modPoolvols(poolvols: dict) -> dict:
    """poolvols - dict of [chainID][basetoken_address][pool_addr] : vol"""
    poolvols2: dict = {}
    for chainID in poolvols:
        chainID2 = chainID
        poolvols2[chainID2] = {}
        for baseaddr in poolvols[chainID]:
            baseaddr2 = baseaddr.lower()
            poolvols2[chainID2][baseaddr2] = {}
            for pool_addr, vol in poolvols[chainID][baseaddr].items():
                pool_addr2 = pool_addr.lower()
                poolvols2[chainID2][baseaddr2][pool_addr2] = vol

    assertPoolvols(poolvols2)
    return poolvols2


def assertPoolvols(poolvols: dict):
    """poolvols - dict of [chainID][basetoken_address][pool_addr] : vol"""
    for chainID in poolvols:
        for basetoken in poolvols[chainID]:
            assert basetoken == basetoken.lower(), basetoken
            for pool_addr in poolvols[chainID][basetoken]:
                assert pool_addr == pool_addr.lower(), pool_addr


def assertPoolvolsUsd(poolvols_USD: dict):
    """poolvols_USD - dict of [chainID][pool_addr] : vol"""
    for chainID in poolvols_USD:
        assertPoolvolsUsdAtChain(poolvols_USD[chainID])


def assertPoolvolsAtChain(poolvols_at_chain: dict):
    """poolvols_at_chain - dict of [basetoken_symbol][pool_addr] : vol"""
    assertPoolvols({FAKE_CHAINID: poolvols_at_chain})


def assertPoolvolsUsdAtChain(poolvols_USD_at_chain: dict):
    """poolvols - dict of [pool_addr] : vol"""
    assertPoolvols({FAKE_CHAINID: {FAKE_TOKEN: poolvols_USD_at_chain}})


def modRates(rates: dict) -> dict:
    """rates - dict of [basetoken_symbol] : USD_per_basetoken"""
    rates2 = {}
    for basetoken, rate in rates.items():
        basetoken2 = basetoken.upper()
        rates2[basetoken2] = rate

    assertRates(rates2)
    return rates2


def assertRates(rates: dict):
    """rates - dict of [basetoken_symbol] : USD_per_basetoken"""
    for basetoken in rates:
        assert basetoken == basetoken.upper(), basetoken
