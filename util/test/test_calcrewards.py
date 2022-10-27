from enforce_typing import enforce_types
import pytest
from pytest import approx

from util.calcrewards import calcRewards, TARGET_WPY

# for shorter lines
RATES = {"OCEAN": 0.5, "H2O": 1.6, "PSDN": 0.01}
C1, C2 = 7, 137
NA, NB = "0xnfta_addr", "0xnftb_addr"
LP1, LP2, LP3 = "0xst1_addr", "0xst2_addr", "0xst3_addr"
OCN_SYMB, H2O_SYMB = "OCEAN", "H2O"
OCN_ADDR, H2O_ADDR = "0xocean", "0xh2o"
SYMBOLS = {
    C1: {OCN_ADDR: OCN_SYMB, H2O_ADDR: H2O_SYMB},
    C2: {"0xocean2": "OCEAN", "Oxh2o2": "H2O"},
}
APPROVED_TOKEN_ADDRS = {C1: [OCN_ADDR, H2O_ADDR], C2: ["0xocean2", "Oxh2o2"]}


@enforce_types
def test_simple():
    stakes = {C1: {NA: {LP1: 1000.0}}}
    nftvols = {C1: {OCN_ADDR: {NA: 1.0}}}

    rewards_avail = 10.0  # in OCEAN

    rewardsperlp, rewardsinfo = _calcRewards(stakes, nftvols, rewards_avail)
    assert rewardsperlp == {C1: {LP1: 10.0}}
    assert rewardsinfo == {C1: {NA: {LP1: 10}}}

    # test helper - just C1
    rewardsperlp, rewardsinfo = _calcRewardsC1(stakes, nftvols, rewards_avail)
    assert rewardsperlp == {LP1: 10.0}
    assert rewardsinfo == {NA: {LP1: 10}}


@enforce_types
def test_two_basetokens_OCEAN_and_H2O():
    stakes = {
        C1: {
            NA: {LP1: 5000.0},
            NB: {LP1: 5000.0},
        }
    }
    nftvols = {
        C1: {OCN_ADDR: {NA: 40.0}, H2O_ADDR: {NB: 12.5}}  # vol in units of OCEAN
    }  # vol in units of H2O

    rewards_avail = 10.0  # in OCEAN
    rewardsperlp, rewardsinfo = _calcRewardsC1(stakes, nftvols, rewards_avail)

    NA_RF_USD = 0.5 * 40.0 * 0.5
    NB_RF_USD = 0.5 * 12.5 * 1.6
    NA_amt = NA_RF_USD / (NA_RF_USD + NB_RF_USD) * 10.0
    NB_amt = NB_RF_USD / (NA_RF_USD + NB_RF_USD) * 10.0

    assert rewardsperlp == {LP1: 10.0}
    assert rewardsinfo == {NA: {LP1: NA_amt}, NB: {LP1: NB_amt}}


# ===================== FIXME FROM HERE ON


@enforce_types
def test_two_chains():
    # first cut: symbols are the same
    stakes = {
        C1: {NA: {LP1: 50000.0}},
        C2: {NB: {LP1: 50000.0}},
    }
    nftvols = {C1: {OCN_ADDR: {NA: 1.0}}, C2: {"0xocean2": {NB: 1.0}}}
    symbols = {
        C1: {OCN_ADDR: OCN_SYMB, H2O_ADDR: H2O_SYMB},
        C2: {"0xocean2": "OCEAN", "Oxh2o2": "H2O"},
    }

    target_rewardsperlp = {C1: {LP1: 10.0}, C2: {LP1: 10.0}}
    target_rewardsinfo = {C1: {NA: {LP1: 10.0}}, C2: {NB: {LP1: 10.0}}}

    rewards_avail = 20.0

    rewardsperlp, rewardsinfo = _calcRewards(
        stakes, nftvols, rewards_avail, symbols=symbols
    )

    assert rewardsperlp == target_rewardsperlp
    assert rewardsinfo == target_rewardsinfo

    # now, make it so that Ocean token in C2 is MOCEAN
    symbols[C2]["0xocean2"] = "MOCEAN"
    rewardsperlp, rewardsinfo = _calcRewards(
        stakes, nftvols, rewards_avail, symbols=symbols
    )

    assert rewardsperlp == {C1: {LP1: 20.0}}  # it completely ignores C2's MOCEAN ...
    assert rewardsinfo == {
        C1: {NA: {LP1: 20.0}}
    }  # ...but of course we don't want that...

    # ... so here's the intervention needed!
    rates = RATES.copy()
    rates["MOCEAN"] = rates["OCEAN"]

    rewardsperlp, rewardsinfo = _calcRewards(
        stakes, nftvols, rewards_avail, rates=rates, symbols=symbols
    )

    # now the rewards should line up as expected
    assert rewardsperlp == target_rewardsperlp
    assert rewardsinfo == target_rewardsinfo


@enforce_types
def test_two_lps_simple():
    stakes = {C1: {NA: {LP1: 100000.0, LP2: 100000.0}}}
    nftvols = {C1: {OCN_ADDR: {NA: 1.0}}}

    rewards_avail = 10.0
    rewardsperlp, rewardsinfo = _calcRewardsC1(stakes, nftvols, rewards_avail)

    assert sum(rewardsperlp.values()) == pytest.approx(10.0, 0.01)
    assert sum(rewardsinfo[NA].values()) == pytest.approx(10.0, 0.01)
    assert rewardsperlp == {LP1: 5.0, LP2: 5.0}
    assert rewardsinfo == {NA: {LP1: 5.0, LP2: 5.0}}


@enforce_types
def test_two_lps_one_with_negligible_stake():
    stakes = {C1: {NA: {LP1: 10000.0, LP2: 1e-14 * 10000.0}}}
    nftvols = {C1: {OCN_ADDR: {NA: 1.0}}}
    rewards_avail = 10.0

    rewardsperlp, rewardsinfo = _calcRewardsC1(stakes, nftvols, rewards_avail)

    assert sum(rewardsperlp.values()) == pytest.approx(10.0, 0.01)
    assert sum(rewardsinfo[NA].values()) == pytest.approx(10.0, 0.01)
    assert rewardsperlp == {LP1: 10.0}  # no entry for LP2
    assert rewardsinfo == {NA: {LP1: 10.0}}  # no entry for LP2


@enforce_types
def test_two_nfts_one_with_volume():
    stakes = {
        C1: {
            NA: {LP1: 10000.0, LP2: 10000.0},
            NB: {LP3: 10000.0},
        }
    }
    nftvols = {C1: {OCN_ADDR: {NA: 1.0}}}  # P1 has volume, but not P2
    rewards_avail = 10.0

    rewardsperlp, rewardsinfo = _calcRewardsC1(stakes, nftvols, rewards_avail)

    assert sum(rewardsperlp.values()) == pytest.approx(10.0, 0.01)
    assert min(rewardsperlp.values()) > 0, "shouldn't have entries with 0 rewards"
    assert rewardsperlp == {LP1: 5.0, LP2: 5.0}

    assert sum(rewardsinfo[NA].values()) == pytest.approx(10.0, 0.01)
    assert min(rewardsinfo[NA].values()) > 0, "shouldn't have entries with 0 rewards"
    assert rewardsinfo == {NA: {LP1: 5.0, LP2: 5.0}}


@enforce_types
def test_two_nfts_both_with_volume():
    stakes = {
        C1: {
            NA: {LP1: 5000.0, LP2: 10000.0},
            NB: {LP1: 5000.0, LP3: 10000.0},
        }
    }
    nftvols = {C1: {OCN_ADDR: {NA: 1.0, NB: 1.0}}}  # P1 & P2 both have volume
    rewards_avail = 10.0

    rewardsperlp, rewardsinfo = _calcRewardsC1(stakes, nftvols, rewards_avail)

    assert sum(rewardsperlp.values()) == pytest.approx(10.0, 0.01)
    assert rewardsperlp[LP1] == rewardsperlp[LP2]
    assert rewardsperlp[LP1] == rewardsperlp[LP3]
    assert rewardsperlp[LP2] == rewardsperlp[LP3]

    assert sum(rewardsinfo[NA].values()) == pytest.approx(5.0, 0.01)
    assert sum(rewardsinfo[NB].values()) == pytest.approx(5.0, 0.01)
    assert rewardsinfo[NA][LP1] == approx(10 / 3 / 2)
    assert rewardsinfo[NB][LP1] == approx(10 / 3 / 2)
    assert rewardsinfo[NA][LP2] == approx(10 / 3)
    assert rewardsinfo[NB][LP3] == approx(10 / 3)


@enforce_types
def test_mix_upper_and_lower_case():
    # setup
    stakes = {C1: {NA: {LP1: 10000.0}}}
    stakes2a = {C1: {NA: {LP1: 10000.0}}}
    stakes2b = {C1: {"0xnfta_aDDr": {LP1: 10000.0}}}
    stakes2c = {C1: {NA: {"0xsT1_aDdR": 10000.0}}}

    nftvols = {C1: {OCN_ADDR: {NA: 10000.0}}}
    nftvols2a = {C1: {OCN_ADDR.upper(): {NA: 10000.0}}}
    nftvols2b = {C1: {OCN_ADDR: {"0xnfta_adDr": 10000.0}}}

    rates2 = {"oceaN": 0.5, "h2O": 1.6}

    target_rewardsperlp = {C1: {LP1: 10.0}}
    target_rewardsinfo = {C1: {NA: {LP1: 10.0}}}
    rewards_avail = 10.0

    # tests
    rewardsperlp, rewardsinfo = _calcRewards(stakes2a, nftvols, rewards_avail)
    assert target_rewardsperlp == rewardsperlp
    assert target_rewardsinfo == rewardsinfo

    rewardsperlp, _ = _calcRewards(stakes2b, nftvols, rewards_avail)
    assert target_rewardsperlp == rewardsperlp
    assert target_rewardsinfo == rewardsinfo

    rewardsperlp, _ = _calcRewards(stakes2c, nftvols, rewards_avail)
    assert target_rewardsperlp == rewardsperlp
    assert target_rewardsinfo == rewardsinfo

    rewardsperlp, _ = _calcRewards(stakes, nftvols2a, rewards_avail)
    assert target_rewardsperlp == rewardsperlp
    assert target_rewardsinfo == rewardsinfo

    rewardsperlp, _ = _calcRewards(stakes, nftvols2b, rewards_avail)
    assert target_rewardsperlp == rewardsperlp
    assert target_rewardsinfo == rewardsinfo

    rewardsperlp, _ = _calcRewards(stakes, nftvols, rewards_avail, rates=rates2)
    assert target_rewardsperlp == rewardsperlp
    assert target_rewardsinfo == rewardsinfo


def test_calcrewards_math():
    ## update this test if the reward function is changed
    stakes = {C1: {NA: {LP1: 20000.0, LP2: 50000.0},
                   NB: {LP1: 20000.0, LP3: 10000.0}}}
    nftvols = {C1: {OCN_ADDR: {NA: 32.0, NB: 8.0}}}
    rewards_avail = 100.0

    rewardsperlp, rewardsinfo = _calcRewardsC1(stakes, nftvols, rewards_avail)

    assert sum(rewardsperlp.values()) == pytest.approx(100.0, 0.01)

    assert rewardsperlp[LP1] == pytest.approx(32.25, 0.01)

    assert rewardsperlp[LP2] == pytest.approx(64.51, 0.01)
    assert rewardsperlp[LP3] == pytest.approx(3.22, 0.01)

    assert rewardsinfo[NA][LP1] == pytest.approx(25.86, 0.01)
    assert rewardsinfo[NA][LP2] == pytest.approx(64.51, 0.01)
    assert rewardsinfo[NB][LP1] == pytest.approx(6.45, 0.01)
    assert rewardsinfo[NB][LP3] == pytest.approx(3.22, 0.01)


@enforce_types
def test_bound_APY_one_nft():
    stakes = {C1: {NA: {LP1: 1.0}}}
    nftvols = {C1: {OCN_ADDR: {NA: 1.0}}}
    rewards_avail = 10000.0

    rewardsperlp, rewardsinfo = _calcRewardsC1(stakes, nftvols, rewards_avail)

    assert rewardsperlp == {LP1: 1.0 * TARGET_WPY}
    assert rewardsinfo == {NA: {LP1: 1.0 * TARGET_WPY}}


@enforce_types
def test_bound_APY_one_LP__high_stake__two_nfts():
    stakes = {C1: {NA: {LP1: 1e6}, NB: {LP1: 1e6}}}
    nftvols = {C1: {OCN_ADDR: {NA: 1.0, NB: 1.0}}}
    rewards_avail = 1000.0

    rewardsperlp, rewardsinfo = _calcRewardsC1(stakes, nftvols, rewards_avail)

    # ensure that total rewards given doesn't exceed rewards_avail
    assert rewardsperlp == {LP1: 1000.0}
    assert rewardsinfo == {NA: {LP1: 500.0}, NB: {LP1: 500.0}}


@enforce_types
def test_bound_APY_two_nfts__equal_low_stake__equal_low_DCV():
    stakes = {C1: {NA: {LP1: 5.0}, NB: {LP2: 5.0}}}
    nftvols = {C1: {OCN_ADDR: {NA: 1.0, NB: 1.0}}}
    rewards_avail = 10000.0

    rewardsperlp, rewardsinfo = _calcRewardsC1(stakes, nftvols, rewards_avail)

    assert rewardsperlp == {LP1: 5.0 * TARGET_WPY, LP2: 5.0 * TARGET_WPY}
    assert rewardsinfo == {NA: {LP1: 5.0 * TARGET_WPY}, NB: {LP2: 5.0 * TARGET_WPY}}


@enforce_types
def test_bound_APY_two_nfts__both_low_stake__one_nft_dominates_stake():
    stakes = {C1: {NA: {LP1: 5.0}, NB: {LP2: 20000.0}}}
    nftvols = {C1: {OCN_ADDR: {NA: 1.0, NB: 1.0}}}
    rewards_avail = 10000.0

    rewardsperlp, rewardsinfo = _calcRewardsC1(stakes, nftvols, rewards_avail)

    # LP1 and LP2 each have stake sufficiently low that TARGET_WPY bounds it.
    # But, LP2 staked more, so it earns more
    assert rewardsperlp == {LP1: 5.0 * TARGET_WPY, LP2: 20000.0 * TARGET_WPY}
    assert rewardsinfo == {
        NA: {LP1: 5.0 * TARGET_WPY},
        NB: {LP2: 20000 * TARGET_WPY},
    }


@enforce_types
def test_bound_APY_two_nfts__low_stake__one_nft_dominates_DCV():
    stakes = {C1: {NA: {LP1: 5.0}, NB: {LP2: 5.0}}}
    nftvols = {C1: {OCN_ADDR: {NA: 1.0, NB: 10000.0}}}
    rewards_avail = 10000.0

    rewardsperlp, rewardsinfo = _calcRewardsC1(stakes, nftvols, rewards_avail)

    # LP1 and LP2 get same amount - they're both bounded because both have low stake
    # Critically, LP2 doesn't swamp LP1 just because LP2's stake * DCV is way higher
    assert rewardsperlp == {LP1: 5.0 * TARGET_WPY, LP2: 5.0 * TARGET_WPY}
    assert rewardsinfo == {NA: {LP1: 5.0 * TARGET_WPY}, NB: {LP2: 5.0 * TARGET_WPY}}


@enforce_types
def test_bound_APY_two_nfts__high_stake__one_nft_dominates_DCV():
    stakes = {C1: {NA: {LP1: 1e6}, NB: {LP2: 1e6}}}
    nftvols = {C1: {OCN_ADDR: {NA: 1.0, NB: 9999.0}}}
    rewards_avail = 10000.0

    rewardsperlp, rewardsinfo = _calcRewardsC1(stakes, nftvols, rewards_avail)

    # LP2 reward swamps LP1 because LP2's stake * DCV is way higher
    assert rewardsperlp == {LP1: 1.0, LP2: 9999.0}
    assert rewardsinfo == {NA: {LP1: 1.0}, NB: {LP2: 9999.0}}


@enforce_types
def test_divide_by_zero():
    stakes = {C1: {NA: {LP1: 10000.0}, NB: {LP2: 10000.0}}}
    nftvols = {C1: {OCN_ADDR: {LP1: 0, LP2: 0}}}
    rewards_avail = 10000.0

    rewardsperlp, _ = _calcRewardsC1(stakes, nftvols, rewards_avail)

    # Should return empty dict because LP1 and LP2 have zero volume
    assert rewardsperlp == {}


# ========================================================================
# Helpers to keep function calls compact, and return vals compact.


@enforce_types
def _calcRewardsC1(
    stakes,
    nftvols,
    rewards_avail,
    symbols=SYMBOLS,
    rates=RATES,
):
    rewardsperlp, rewardsinfo = _calcRewards(
        stakes, nftvols, rewards_avail, symbols, rates
    )
    rewardsperlp = {} if not rewardsperlp else rewardsperlp[C1]
    rewardsinfo = {} if not rewardsinfo else rewardsinfo[C1]
    return rewardsperlp, rewardsinfo


@enforce_types
def _calcRewards(
    stakes,
    nftvols,
    rewards_avail,
    symbols=SYMBOLS,
    rates=RATES,
):
    """Helper. Fills in SYMBOLS and RATES, to keep calls compact"""
    return calcRewards(stakes, nftvols, symbols, rates, rewards_avail)
