# 'modX' functions modify 'X' to follow rules: lowercase address,uppercase token,"0x" in address
# 'assertX' functions asserts that 'X' follows the rules

from enforce_typing import enforce_types


FAKE_CHAINID = 99
FAKE_TOKEN_ADDR = "0xfake_token"


@enforce_types
def modTuple(stakes, poolvols, rates) -> tuple:
    return (modAllocations(stakes), modPoolvols(poolvols), modRates(rates))


@enforce_types
def modAllocations(stakes: dict) -> dict:
    """stakes - dict of [chainID][nft_addr][LP_addr] : percentage"""
    allocations: dict = {}
    for chainID in stakes:
        chainID2 = chainID
        allocations[chainID2] = {}
        for nft_addr in stakes[chainID]:
            base_addr2 = nft_addr.lower()
            allocations[chainID2][base_addr2] = {}
            for LP_addr, st in stakes[chainID][nft_addr]:
                allocations[chainID2][base_addr2][LP_addr] = st

    asserAllocations(allocations)
    return allocations


@enforce_types
def asserAllocations(stakes: dict):
    """stakes - dict of [chainID][nft_addr][LP_addr] : stake"""
    for chainID in stakes:
        for nft_addr in stakes[chainID]:
            for LP_addr in stakes[chainID][nft_addr]:
                assert isinstance(stakes[chainID][nft_addr][LP_addr], float)
                assert 0.0 <= stakes[chainID][nft_addr][LP_addr] <= 1.0


@enforce_types
def assertStakesUsd(stakes_USD: dict):
    """stakes_USD - dict of [chainID][pool_addr][LP_addr] : stake"""
    for chainID in stakes_USD:
        assertStakesUsdAtChain(stakes_USD[chainID])


@enforce_types
def assertStakesAtChain(stakes_at_chain: dict):
    """stakes_at_chain - dict of [basetoken_address][pool_addr][LP_addr] : stake"""
    asserAllocations({FAKE_CHAINID: stakes_at_chain})


@enforce_types
def assertStakesUsdAtChain(stakes_at_chain: dict):
    """stakes_USD_at_chain - dict of [pool_addr][LP_addr] : stake"""
    asserAllocations({FAKE_CHAINID: {FAKE_TOKEN_ADDR: stakes_at_chain}})


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

    assertNFTvols(poolvols2)
    return poolvols2


@enforce_types
def assertNFTvols(poolvols: dict):
    """poolvols - dict of [chainID][basetoken_address][nft_addr] : vol"""
    for chainID in poolvols:
        for base_addr in poolvols[chainID]:
            assert base_addr == base_addr.lower(), base_addr
            assert base_addr[:2] == "0x", base_addr
            for nft_addr in poolvols[chainID][base_addr]:
                assert nft_addr == nft_addr.lower(), nft_addr
                assert nft_addr[:2] == "0x", nft_addr


@enforce_types
def assertPoolvolsUsd(poolvols_USD: dict):
    """poolvols_USD - dict of [chainID][pool_addr] : vol"""
    for chainID in poolvols_USD:
        assertPoolvolsUsdAtChain(poolvols_USD[chainID])


@enforce_types
def assertPoolvolsAtChain(poolvols_at_chain: dict):
    """poolvols_at_chain - dict of [basetoken_address][pool_addr] : vol"""
    assertNFTvols({FAKE_CHAINID: poolvols_at_chain})


@enforce_types
def assertPoolvolsUsdAtChain(poolvols_USD_at_chain: dict):
    """poolvols - dict of [pool_addr] : vol"""
    assertNFTvols({FAKE_CHAINID: {FAKE_TOKEN_ADDR: poolvols_USD_at_chain}})


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
