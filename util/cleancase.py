# 'modX' functions modify 'X' to follow rules: lowercase address,uppercase token,"0x" in address
# 'assertX' functions asserts that 'X' follows the rules

from enforce_typing import enforce_types


FAKE_CHAINID = 99
FAKE_TOKEN_ADDR = "0xfake_token"


@enforce_types
def modAllocations(allocs: dict) -> dict:
    """allocs - dict of [chainID][nft_addr][LP_addr] : LP's % alloc"""
    allocs2: dict = {}
    for chainID in allocs:
        chainID2 = int(chainID)
        allocs2[chainID2] = {}
        for nft_addr in allocs[chainID]:
            nft_addr2 = nft_addr.lower()
            allocs2[chainID2][nft_addr2] = {}
            for LP_addr, alloc in allocs[chainID][nft_addr].items():
                LP_addr2 = LP_addr.lower()
                allocs2[chainID2][nft_addr2][LP_addr2] = alloc
    assertAllocations(allocs2)
    return allocs2


@enforce_types
def assertAllocations(allocs: dict):
    """allocations - dict of [chainID][nft_addr][LP_addr] : LP's % alloc"""
    lpsum = {}
    for chainID in allocs:
        assert isinstance(chainID, int)
        for nft_addr in allocs[chainID]:
            assert nft_addr[:2] == "0x", nft_addr
            assert nft_addr.lower() == nft_addr, nft_addr
            for LP_addr, alloc in allocs[chainID][nft_addr].items():
                assert isinstance(alloc, float)
                if LP_addr not in lpsum:
                    lpsum[LP_addr] = 0.0
                lpsum[LP_addr] += float(alloc)

    for LP_addr in lpsum:
        assert (
            lpsum[LP_addr] <= 1.0 + 1e-5
        ), f"LP {LP_addr} has {lpsum[LP_addr]}% allocation, > 1.0%"


@enforce_types
def modStakes(stakes: dict) -> dict:
    """stakes - dict of [chainID][nft_addr][LP_addr] : LP's absolute alloc"""
    stakes2: dict = {}
    for chainID in stakes:
        chainID2 = int(chainID)
        stakes2[chainID2] = {}
        for nft_addr in stakes[chainID]:
            nft_addr2 = nft_addr.lower()
            stakes2[chainID2][nft_addr2] = {}
            for LP_addr, alloc in stakes[chainID][nft_addr].items():
                LP_addr2 = LP_addr.lower()
                stakes2[chainID2][nft_addr2][LP_addr2] = alloc
    assertStakes(stakes2)
    return stakes2


@enforce_types
def assertStakes(stakes: dict):
    """stakes - dict of [chainID][nft_addr][LP_addr] : stake"""
    # stakes are like allocations, except absolute not %. But, we can't
    # reuse assertAllocations() here because it tests for sum(vals) == 1.0
    for chainID in stakes:
        assert isinstance(chainID, int)
        for nft_addr in stakes[chainID]:
            assert nft_addr[:2] == "0x", nft_addr
            assert nft_addr.lower() == nft_addr, nft_addr
            for stake in stakes[chainID][nft_addr].values():
                assert isinstance(stake, float)


@enforce_types
def modVebals(vebals: dict) -> dict:
    """vebals - dict of [LP_addr] : LP's ve balance"""
    vebals2 = {}
    for LP_addr, bal in vebals.items():
        LP_addr2 = LP_addr.lower()
        vebals2[LP_addr2] = bal

    assertVebals(vebals2)
    return vebals2


@enforce_types
def assertVebals(vebals: dict):
    """vebals - dict of [LP_addr] : LP's ve balance"""
    for LP_addr in vebals:
        assert LP_addr[:2] == "0x", LP_addr
        assert LP_addr == LP_addr.lower(), LP_addr


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
