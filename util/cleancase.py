# 'modX' functions modify 'X' to follow rules: lowercase address,uppercase token,"0x" in address
# 'assertX' functions asserts that 'X' follows the rules

from enforce_typing import enforce_types


FAKE_CHAINID = 99
FAKE_TOKEN_ADDR = "0xfake_token"


@enforce_types
def modTuple(stakes, poolvols, rates) -> tuple:
    return (modStakes(stakes), modPoolvols(poolvols), modRates(rates))


@enforce_types
def modStakes(stakes: dict) -> dict:
    """stakes - dict of [chainID][basetoken_address][pool_addr][LP_addr] : stake"""
    stakes2: dict = {}
    for chainID in stakes:
        chainID2 = chainID
        stakes2[chainID2] = {}
        for base_addr in stakes[chainID]:
            base_addr2 = base_addr.lower()
            stakes2[chainID2][base_addr2] = {}
            for pool_addr in stakes[chainID][base_addr]:
                pool_addr2 = pool_addr.lower()
                stakes2[chainID2][base_addr2][pool_addr2] = {}
                for LP_addr, st in stakes[chainID][base_addr][pool_addr].items():
                    LP_addr2 = LP_addr.lower()
                    stakes2[chainID2][base_addr2][pool_addr2][LP_addr2] = st

    assertStakes(stakes2)
    return stakes2


@enforce_types
def assertStakes(stakes: dict):
    """stakes - dict of [chainID][basetoken_address][pool_addr][LP_addr] : stake"""
    for chainID in stakes:
        for base_addr in stakes[chainID]:
            assert base_addr == base_addr.lower(), base_addr
            assert base_addr[:2] == "0x", base_addr
            for pool_addr in stakes[chainID][base_addr]:
                assert pool_addr == pool_addr.lower(), pool_addr
                assert pool_addr[:2] == "0x", pool_addr
                for LP_addr in stakes[chainID][base_addr][pool_addr]:
                    assert LP_addr == LP_addr.lower(), LP_addr
                    assert LP_addr[:2] == "0x", LP_addr


@enforce_types
def assertStakesUsd(stakes_USD: dict):
    """stakes_USD - dict of [chainID][pool_addr][LP_addr] : stake"""
    for chainID in stakes_USD:
        assertStakesUsdAtChain(stakes_USD[chainID])


@enforce_types
def assertStakesAtChain(stakes_at_chain: dict):
    """stakes_at_chain - dict of [basetoken_address][pool_addr][LP_addr] : stake"""
    assertStakes({FAKE_CHAINID: stakes_at_chain})


@enforce_types
def assertStakesUsdAtChain(stakes_at_chain: dict):
    """stakes_USD_at_chain - dict of [pool_addr][LP_addr] : stake"""
    assertStakes({FAKE_CHAINID: {FAKE_TOKEN_ADDR: stakes_at_chain}})


@enforce_types
def modPoolvols(poolvols: dict) -> dict:
    """poolvols - dict of [chainID][basetoken_address][pool_addr] : vol"""
    poolvols2: dict = {}
    for chainID in poolvols:
        chainID2 = chainID
        poolvols2[chainID2] = {}
        for base_addr in poolvols[chainID]:
            base_addr2 = base_addr.lower()
            poolvols2[chainID2][base_addr2] = {}
            for pool_addr, vol in poolvols[chainID][base_addr].items():
                pool_addr2 = pool_addr.lower()
                poolvols2[chainID2][base_addr2][pool_addr2] = vol

    assertPoolvols(poolvols2)
    return poolvols2


@enforce_types
def assertPoolvols(poolvols: dict):
    """poolvols - dict of [chainID][basetoken_address][pool_addr] : vol"""
    for chainID in poolvols:
        for base_addr in poolvols[chainID]:
            assert base_addr == base_addr.lower(), base_addr
            assert base_addr[:2] == "0x", base_addr
            for pool_addr in poolvols[chainID][base_addr]:
                assert pool_addr == pool_addr.lower(), pool_addr
                assert pool_addr[:2] == "0x", pool_addr


@enforce_types
def assertPoolvolsUsd(poolvols_USD: dict):
    """poolvols_USD - dict of [chainID][pool_addr] : vol"""
    for chainID in poolvols_USD:
        assertPoolvolsUsdAtChain(poolvols_USD[chainID])


@enforce_types
def assertPoolvolsAtChain(poolvols_at_chain: dict):
    """poolvols_at_chain - dict of [basetoken_address][pool_addr] : vol"""
    assertPoolvols({FAKE_CHAINID: poolvols_at_chain})


@enforce_types
def assertPoolvolsUsdAtChain(poolvols_USD_at_chain: dict):
    """poolvols - dict of [pool_addr] : vol"""
    assertPoolvols({FAKE_CHAINID: {FAKE_TOKEN_ADDR: poolvols_USD_at_chain}})


@enforce_types
def modRates(rates: dict) -> dict:
    """rates - dict of [basetoken_symbol] : USD_per_basetoken"""
    rates2 = {}
    for base_symb, rate in rates.items():
        base_symb2 = base_symb.upper()
        rates2[base_symb2] = rate

    assertRates(rates2)
    return rates2


@enforce_types
def assertRates(rates: dict):
    """rates - dict of [basetoken_symbol] : USD_per_basetoken"""
    for base_symb in rates:
        assert base_symb == base_symb.upper(), base_symb
        assert base_symb[:2] != "0x"
