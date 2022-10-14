# 'modX' functions modify 'X' to follow rules: lowercase address,uppercase token,"0x" in address
# 'assertX' functions asserts that 'X' follows the rules

from enforce_typing import enforce_types


FAKE_CHAINID = 99
FAKE_TOKEN_ADDR = "0xfake_token"


@enforce_types
def modTuple(allocations, nftvols, rates) -> tuple:
    return (modAllocations(allocations), modNFTvols(nftvols), modRates(rates))


@enforce_types
def modAllocations(allocations: dict) -> dict:
    """allocations - dict of [chainID][nft_addr][LP_addr] : percentage"""
    allocations2: dict = {}
    for chainID in allocations:
        chainID2 = int(chainID)
        allocations2[chainID2] = {}
        for nft_addr in allocations[chainID]:
            nft_addr2 = nft_addr.lower()
            allocations2[chainID2][nft_addr2] = {}
            for LP_addr in allocations[chainID][nft_addr]:
                LP_addr2 = LP_addr.lower()
                allocations2[chainID2][nft_addr2][LP_addr2] = allocations[chainID][
                    nft_addr
                ][LP_addr]
    assertAllocations(allocations2)
    return allocations2


@enforce_types
def assertStakes(allcs: dict):
    """stakes - dict of [chainID][nft_addr][LP_addr] : stake"""
    for chainID in allcs:
        assert isinstance(chainID, int)
        for nft_addr in allcs[chainID]:
            assert nft_addr[:2] == "0x", nft_addr
            assert nft_addr.lower() == nft_addr, nft_addr
            for LP_addr in allcs[chainID][nft_addr]:
                assert isinstance(allcs[chainID][nft_addr][LP_addr], float)


@enforce_types
def assertAllocations(allcs: dict):
    """allocations - dict of [chainID][nft_addr][LP_addr] : percent"""
    lpsum = {}
    for chainID in allcs:
        assert isinstance(chainID, int)
        for nft_addr in allcs[chainID]:
            assert nft_addr[:2] == "0x", nft_addr
            assert nft_addr.lower() == nft_addr, nft_addr
            for LP_addr in allcs[chainID][nft_addr]:
                assert isinstance(allcs[chainID][nft_addr][LP_addr], float)
                if LP_addr not in lpsum:
                    lpsum[LP_addr] = 0
                lpsum[LP_addr] += allcs[chainID][nft_addr][LP_addr]
    for LP_addr in lpsum:
        assert (
            lpsum[LP_addr] <= 1.0
        ), f"LP {LP_addr} has {lpsum[LP_addr]}% allocation, > 1.0%"


@enforce_types
def assertStakesUsd(stakes_USD: dict):
    """stakes_USD - dict of [chainID][nft_addr][LP_addr] : stake"""
    for chainID in stakes_USD:
        for nftaddr in stakes_USD[chainID]:
            assertStakesUsdAtChain(stakes_USD[chainID][nftaddr])


@enforce_types
def assertStakesAtChain(stakes_at_chain: dict):
    """stakes_at_chain - dict of [basetoken_address][NFT_addr][LP_addr] : stake"""
    assertStakes({FAKE_CHAINID: stakes_at_chain})


@enforce_types
def assertStakesUsdAtChain(stakes_at_chain: dict):
    """stakes_USD_at_chain - dict of [NFT_addr][LP_addr] : stake"""
    assertStakes({FAKE_CHAINID: {FAKE_TOKEN_ADDR: stakes_at_chain}})


@enforce_types
def modNFTvols(nftvols: dict) -> dict:
    """nftvols - dict of [chainID][basetoken_address][NFT_addr] : vol"""
    nftvols2: dict = {}
    for chainID in nftvols:
        chainID2 = chainID
        nftvols2[chainID2] = {}
        for base_addr in nftvols[chainID]:
            base_addr2 = base_addr.lower()
            nftvols2[chainID2][base_addr2] = {}
            for NFT_addr, vol in nftvols[chainID][base_addr].items():
                NFT_addr2 = NFT_addr.lower()
                nftvols2[chainID2][base_addr2][NFT_addr2] = vol

    assertNFTvols(nftvols2)
    return nftvols2


@enforce_types
def assertNFTvols(nftvols: dict):
    """nftvols - dict of [chainID][basetoken_address][nft_addr] : vol"""
    for chainID in nftvols:
        for base_addr in nftvols[chainID]:
            assert base_addr == base_addr.lower(), base_addr
            assert base_addr[:2] == "0x", base_addr
            for nft_addr in nftvols[chainID][base_addr]:
                assert nft_addr == nft_addr.lower(), nft_addr
                assert nft_addr[:2] == "0x", nft_addr


@enforce_types
def assertNFTvolUsd(nftvols_USD: dict):
    """nftvols_USD - dict of [chainID][NFT_addr] : vol"""
    for chainID in nftvols_USD:
        assertNFTvolsUsdAtChain(nftvols_USD[chainID])


@enforce_types
def assertNFTvolsAtChain(nftvols_at_chain: dict):
    """nftvols_at_chain - dict of [basetoken_address][pool_addr] : vol"""
    assertNFTvols({FAKE_CHAINID: nftvols_at_chain})


@enforce_types
def assertNFTvolsUsdAtChain(nftvols_USD_at_chain: dict):
    """nftvols - dict of [NFT_addr] : vol"""
    assertNFTvols({FAKE_CHAINID: {FAKE_TOKEN_ADDR: nftvols_USD_at_chain}})


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
