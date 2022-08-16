# 'modX' functions modify 'X' to follow rules: lowercase address,uppercase token,"0x" in address
# 'assertX' functions asserts that 'X' follows the rules

from enforce_typing import enforce_types


FAKE_CHAINID = 99
FAKE_TOKEN_ADDR = "0xfake_token"


@enforce_types
def modTuple(allocations, poolvols, rates) -> tuple:
    return (modAllocations(allocations), modNFTvols(poolvols), modRates(rates))


@enforce_types
def modAllocations(allocations: dict) -> dict:
    """allocations - dict of [chainID][nft_addr][LP_addr] : percentage"""
    allocations2: dict = {}
    for chainID in allocations:
        chainID2 = chainID
        allocations2[chainID2] = {}
        for nft_addr in allocations[chainID]:
            nft_addr2 = nft_addr.lower()
            allocations2[chainID2][nft_addr2] = {}
            for LP_addr in allocations[chainID][nft_addr]:
                allocations2[chainID2][nft_addr2][LP_addr] = allocations[chainID][
                    nft_addr
                ][LP_addr]
    assertAllocations(allocations2)
    return allocations2


@enforce_types
def assertAllocations(allcs: dict):
    """stakes - dict of [chainID][nft_addr][LP_addr] : stake"""
    for chainID in allcs:
        for nft_addr in allcs[chainID]:
            for LP_addr in allcs[chainID][nft_addr]:
                assert isinstance(allcs[chainID][nft_addr][LP_addr], float)


@enforce_types
def assertStakesUsd(stakes_USD: dict):
    """stakes_USD - dict of [chainID][nft_addr][LP_addr] : stake"""
    for chainID in stakes_USD:
        for nftaddr in stakes_USD[chainID]:
            assertStakesUsdAtChain(stakes_USD[chainID][nftaddr])


@enforce_types
def assertStakesAtChain(stakes_at_chain: dict):
    """stakes_at_chain - dict of [basetoken_address][pool_addr][LP_addr] : stake"""
    assertAllocations({FAKE_CHAINID: stakes_at_chain})


@enforce_types
def assertStakesUsdAtChain(stakes_at_chain: dict):
    """stakes_USD_at_chain - dict of [pool_addr][LP_addr] : stake"""
    assertAllocations({FAKE_CHAINID: {FAKE_TOKEN_ADDR: stakes_at_chain}})


@enforce_types
def modNFTvols(poolvols: dict) -> dict:
    """poolvols - dict of [chainID][basetoken_address][pool_addr] : vol"""
    nftvols2: dict = {}
    for chainID in poolvols:
        chainID2 = chainID
        nftvols2[chainID2] = {}
        for base_addr in poolvols[chainID]:
            base_addr2 = base_addr.lower()
            nftvols2[chainID2][base_addr2] = {}
            for pool_addr, vol in poolvols[chainID][base_addr].items():
                pool_addr2 = pool_addr.lower()
                nftvols2[chainID2][base_addr2][pool_addr2] = vol

    assertNFTvols(nftvols2)
    return nftvols2


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
