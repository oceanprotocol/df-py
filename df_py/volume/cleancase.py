# 'modX' functions modify 'X' to follow rules: lowercase address,uppercase token,"0x" in address
# 'assertX' functions asserts that 'X' follows the rules

from enforce_typing import enforce_types

FAKE_CHAINID = 99
FAKE_TOKEN_ADDR = "0xfake_token"


@enforce_types
def mod_allocations(allocs: dict) -> dict:
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
    assert_allocations(allocs2)
    return allocs2


@enforce_types
def assert_allocations(allocs: dict):
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
def mod_stakes(stakes: dict) -> dict:
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
    assert_stakes(stakes2)
    return stakes2


@enforce_types
def assert_stakes(stakes: dict):
    """stakes - dict of [chainID][nft_addr][LP_addr] : stake"""
    # stakes are like allocations, except absolute not %. But, we can't
    # reuse assert_allocations() here because it tests for sum(vals) == 1.0
    for chainID in stakes:
        assert isinstance(chainID, int)
        for nft_addr in stakes[chainID]:
            assert nft_addr[:2] == "0x", nft_addr
            assert nft_addr.lower() == nft_addr, nft_addr
            for stake in stakes[chainID][nft_addr].values():
                assert isinstance(stake, float)


@enforce_types
def mod_vebals(vebals: dict) -> dict:
    """vebals - dict of [LP_addr] : LP's ve balance"""
    vebals2 = {}
    for LP_addr, bal in vebals.items():
        LP_addr2 = LP_addr.lower()
        vebals2[LP_addr2] = bal

    assert_vebals(vebals2)
    return vebals2


@enforce_types
def assert_vebals(vebals: dict):
    """vebals - dict of [LP_addr] : LP's ve balance"""
    for LP_addr in vebals:
        assert LP_addr[:2] == "0x", LP_addr
        assert LP_addr == LP_addr.lower(), LP_addr


@enforce_types
def mod_nft_vols(nftvols: dict) -> dict:
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

    assert_nft_vols(nftvols2)
    return nftvols2


@enforce_types
def assert_nft_vols(nftvols: dict):
    """nftvols - dict of [chainID][basetoken_address][nft_addr] : vol"""
    for chainID in nftvols:
        for base_addr in nftvols[chainID]:
            assert base_addr == base_addr.lower(), base_addr
            assert base_addr[:2] == "0x", base_addr
            for nft_addr in nftvols[chainID][base_addr]:
                assert nft_addr == nft_addr.lower(), nft_addr
                assert nft_addr[:2] == "0x", nft_addr


@enforce_types
def mod_symbols(symbols: dict) -> dict:
    """symbols - dict of [chainID][basetoken_address] : symbol"""
    symbols2: dict = {}
    for chainID in symbols:
        chainID2 = chainID
        symbols2[chainID2] = {}
        for base_addr, symbol in symbols[chainID].items():
            base_addr2 = base_addr.lower()
            symbol2 = symbol.upper()
            symbols2[chainID2][base_addr2] = symbol2

    assert_symbols(symbols2)
    return symbols2


@enforce_types
def assert_symbols(symbols: dict):
    """nftvols - dict of [chainID][basetoken_address] : symbol"""
    for chainID in symbols:
        for base_addr, symbol in symbols[chainID].items():
            assert base_addr == base_addr.lower(), base_addr
            assert base_addr[:2] == "0x", base_addr
            assert symbol == symbol.upper(), symbol


@enforce_types
def mod_rates(rates: dict) -> dict:
    """rates - dict of [basetoken_symbol] : USD_per_basetoken"""
    rates2 = {}
    for base_symb, rate in rates.items():
        base_symb2 = base_symb.upper()
        rates2[base_symb2] = rate

    assert_rates(rates2)
    return rates2


@enforce_types
def assert_rates(rates: dict):
    """rates - dict of [basetoken_symbol] : USD_per_basetoken"""
    for base_symb in rates:
        assert base_symb == base_symb.upper(), base_symb
        assert base_symb[:2] != "0x"


@enforce_types
def mod_owners(owners: dict) -> dict:
    """owners - dict of [chainID][nft_addr] : owner_addr"""
    owners2: dict = {}
    for chainID in owners:
        chainID2 = chainID
        owners2[chainID2] = {}
        for nft_addr, owner_addr in owners[chainID].items():
            nft_addr2 = nft_addr.lower()
            owner_addr2 = owner_addr.lower()
            owners2[chainID2][nft_addr2] = owner_addr2

    assert_owners(owners2)
    return owners2


@enforce_types
def assert_owners(owners: dict):
    """nftvols - dict of [chainID][nft_addr] : owner_addr"""
    for chainID in owners:
        for nft_addr, owner_addr in owners[chainID].items():
            assert nft_addr == nft_addr.lower(), nft_addr
            assert nft_addr[:2] == "0x", nft_addr
            assert owner_addr == owner_addr.lower(), owner_addr
            assert owner_addr[:2] == "0x", owner_addr
