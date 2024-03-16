
# ========================================================================
# Test rank-based allocate -- end-to-end with calc_rewards()
@patch(
    "df_py.volume.reward_calc_main.query_predictoor_contracts",
    MagicMock(return_value={}),
)
@enforce_types
def test_rank_1_nft():
    stakes = {C1: {NA: {LP1: 1000.0}}}
    nftvols = {C1: {OCN_ADDR: {NA: 1.0}}}
    OCEAN_avail = 10.0

    rew, _ = _calc_rewards_C1(stakes, nftvols, OCEAN_avail, do_rank=True)
    assert rew == {LP1: 10.0}


@patch(
    "df_py.volume.reward_calc_main.query_predictoor_contracts",
    MagicMock(return_value={}),
)
@enforce_types
def test_rank_3_nfts():
    stakes = {C1: {NA: {LP1: 1000.0}, NB: {LP2: 1000.0}, NC: {LP3: 1000.0}}}
    OCEAN_avail = 10.0

    # equal volumes
    nftvols = {C1: {OCN_ADDR: {NA: 1.0, NB: 1.0, NC: 1.0}}}
    rew, _ = _calc_rewards_C1(stakes, nftvols, OCEAN_avail, do_rank=True)
    assert sorted(rew.keys()) == [LP1, LP2, LP3]
    assert sum(rew.values()) == pytest.approx(10.0, 0.01)
    for LP in [LP1, LP2, LP3]:
        assert rew[LP] == pytest.approx(10.0 / 3.0)

    # unequal volumes
    nftvols = {C1: {OCN_ADDR: {NA: 1.0, NB: 0.002, NC: 0.001}}}
    rew, _ = _calc_rewards_C1(stakes, nftvols, OCEAN_avail, do_rank=True)
    assert sorted(rew.keys()) == [LP1, LP2, LP3]
    assert sum(rew.values()) == pytest.approx(10.0, 0.01)
    assert rew[LP1] > rew[LP2] > rew[LP3], rew
    assert rew[LP1] > 3.33, rew
    assert rew[LP2] > 1.0, rew  # if it was pro-rata it would have been << 1.0
    assert rew[LP3] > 1.0, rew  # ""


@patch(
    "df_py.volume.reward_calc_main.query_predictoor_contracts",
    MagicMock(return_value={}),
)
@enforce_types
def test_rank_10_NFTs():
    _test_rank_N_NFTs(10)


@patch(
    "df_py.volume.reward_calc_main.query_predictoor_contracts",
    MagicMock(return_value={}),
)
@enforce_types
def test_rank_200_NFTs():
    _test_rank_N_NFTs(200)


@patch(
    "df_py.volume.reward_calc_main.query_predictoor_contracts",
    MagicMock(return_value={}),
)
@enforce_types
def _test_rank_N_NFTs(N: int):
    OCEAN_avail = 10.0

    # equal volumes
    (_, LP_addrs, stakes, nftvols) = _rank_testvals(N, equal_vol=True)
    rew, _ = _calc_rewards_C1(stakes, nftvols, OCEAN_avail, do_rank=True)
    assert len(rew) == N
    assert LP_addrs == sorted(rew.keys())
    assert sum(rew.values()) == pytest.approx(10.0, 0.01)
    assert min(rew.values()) == max(rew.values())

    # unequal volumes
    (_, LP_addrs, stakes, nftvols) = _rank_testvals(N, equal_vol=False)
    rew, _ = _calc_rewards_C1(stakes, nftvols, OCEAN_avail, do_rank=True)
    max_N = min(N, constants.MAX_N_RANK_ASSETS)
    assert len(rew) == max_N
    assert LP_addrs[:max_N] == sorted(rew.keys())
    assert sum(rew.values()) == pytest.approx(10.0, 0.01)
    assert min(rew.values()) > 0.0
    for i in range(1, N):
        if i >= max_N:
            # if reward is zero, then it shouldn't even show up in rewards dict
            assert LP_addrs[i] not in rew
        else:
            assert rew[LP_addrs[i]] < rew[LP_addrs[i - 1]]


@enforce_types
def _rank_testvals(N: int, equal_vol: bool) -> Tuple[list, list, dict, dict]:
    NFT_addrs = [f"0xnft_{i:03}" for i in range(N)]
    LP_addrs = [f"0xlp_{i:03}" for i in range(N)]
    stakes: dict = {C1: {}}
    nftvols: dict = {C1: {OCN_ADDR: {}}}
    for i, (NFT_addr, LP_addr) in enumerate(zip(NFT_addrs, LP_addrs)):
        stakes[C1][NFT_addr] = {LP_addr: 1000.0}
        if equal_vol:
            vol = 1.0
        else:
            vol = max(N, 1000.0) - float(i)
        nftvols[C1][OCN_ADDR][NFT_addr] = vol
    return (NFT_addrs, LP_addrs, stakes, nftvols)

