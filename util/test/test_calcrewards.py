from datetime import datetime, timedelta

from enforce_typing import enforce_types
import numpy as np
import pytest
from pytest import approx

from util import calcrewards
from util.calcrewards import calcRewards, TARGET_WPY

# for shorter lines
RATES = {"OCEAN": 0.5, "H2O": 1.6, "PSDN": 0.01}
C1, C2 = 7, 137
NA, NB = "0xnfta_addr", "0xnftb_addr"
LP1, LP2, LP3, LP4 = "0xlp1_addr", "0xlp2_addr", "0xlp3_addr", "0xlp4_addr"
OCN_SYMB, H2O_SYMB = "OCEAN", "H2O"
OCN_ADDR, H2O_ADDR = "0xocean", "0xh2o"
OCN_ADDR2, H2O_ADDR2 = "0xocean2", "Oxh2o2"
SYMBOLS = {
    C1: {OCN_ADDR: OCN_SYMB, H2O_ADDR: H2O_SYMB},
    C2: {OCN_ADDR2: OCN_SYMB, H2O_ADDR2: H2O_SYMB},
}
APPROVED_TOKEN_ADDRS = {C1: [OCN_ADDR, H2O_ADDR], C2: [OCN_ADDR2, H2O_ADDR2]}


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
    nftvols = {C1: {OCN_ADDR: {NA: 1.0}}, C2: {OCN_ADDR2: {NB: 1.0}}}
    symbols = {
        C1: {OCN_ADDR: OCN_SYMB, H2O_ADDR: H2O_SYMB},
        C2: {OCN_ADDR2: OCN_SYMB, H2O_ADDR2: H2O_SYMB},
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
    symbols[C2][OCN_ADDR2] = "MOCEAN"
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

    assert sum(rewardsperlp.values()) == pytest.approx(10.0, 1e-5)
    assert LP2 not in rewardsperlp

    assert rewardsinfo[NA][LP1] == pytest.approx(10.0, 1e-6)
    assert LP2 not in rewardsinfo[NA]


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
    stakes2c = {C1: {NA: {"0xlP1_aDdR": 10000.0}}}

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
    ## update this test when the reward function is changed
    stakes = {C1: {NA: {LP1: 1.0e6, LP2: 9.0e6}, NB: {LP3: 10.0e6, LP4: 90.0e6}}}
    nftvols = {C1: {OCN_ADDR: {NA: 0.5e6, NB: 0.5e6}}}
    rewards_avail = 5000.0

    rewardsperlp, _ = _calcRewardsC1(stakes, nftvols, rewards_avail)

    assert sum(rewardsperlp.values()) == pytest.approx(rewards_avail, 0.01)

    assert rewardsperlp[LP1] == pytest.approx(250.0, 0.01)
    assert rewardsperlp[LP2] == pytest.approx(2250.0, 0.01)
    assert rewardsperlp[LP3] == pytest.approx(250.0, 0.01)
    assert rewardsperlp[LP4] == pytest.approx(2250.0, 0.01)


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
def test_bound_budget_by_DCT():
    pass  # placeholder


@enforce_types
def test_divide_by_zero():
    stakes = {C1: {NA: {LP1: 10000.0}, NB: {LP2: 10000.0}}}
    nftvols = {C1: {OCN_ADDR: {LP1: 0, LP2: 0}}}
    rewards_avail = 10000.0

    rewardsperlp, _ = _calcRewardsC1(stakes, nftvols, rewards_avail)

    # Should return empty dict because LP1 and LP2 have zero volume
    assert rewardsperlp == {}


# ========================================================================
# Tests around bounding rewards by DCV


@enforce_types
def test_totalDcv():
    totDcv = calcrewards.totalDcv
    SYM, R, O, H, O2 = SYMBOLS, RATES, OCN_ADDR, H2O_ADDR, OCN_ADDR2

    assert totDcv({C1: {O: {NA: 1.0}}}, SYM, R) == 1.0
    assert totDcv({C1: {O: {NA: 0.5, NB: 0.5}}}, SYM, R) == 1.0
    assert totDcv({C1: {O: {NA: 0.25, NB: 0.25}}, C2: {O2: {NA: 0.5}}}, SYM, R) == 1.0
    assert totDcv({C1: {H: {NA: 1.0}}}, SYM, R) == 1.6 / 0.5  # 1 H2O = 1.6 USD
    assert totDcv({C1: {O: {NA: 1.0}, H: {NB: 1.0}}}, SYM, R) == (1.0 + 1.6 / 0.5)


@enforce_types
def test_getDFWeekNumber():
    wkNbr = calcrewards.getDfWeekNumber

    # test DF5. Counting starts Thu Sep 29, 2022. Last day is Wed Oct 5, 2022
    assert wkNbr(datetime(2022, 9, 28)) == -1  # Wed
    assert wkNbr(datetime(2022, 9, 29)) == 5  # Thu
    assert wkNbr(datetime(2022, 9, 30)) == 5  # Fri
    assert wkNbr(datetime(2022, 10, 5)) == 5  # Wed
    assert wkNbr(datetime(2022, 10, 6)) == 6  # Thu
    assert wkNbr(datetime(2022, 10, 12)) == 6  # Wed
    assert wkNbr(datetime(2022, 10, 13)) == 7  # Thu

    # test DF9. Start Thu Oct 27. Last day is Wed Nov 2, 2022,
    assert wkNbr(datetime(2022, 10, 25)) == 8  # Wed
    assert wkNbr(datetime(2022, 10, 26)) == 8  # Wed
    assert wkNbr(datetime(2022, 10, 27)) == 9  # Thu
    assert wkNbr(datetime(2022, 10, 28)) == 9  # Fri
    assert wkNbr(datetime(2022, 11, 2)) == 9  # Wed
    assert wkNbr(datetime(2022, 11, 3)) == 10  # Thu
    assert wkNbr(datetime(2022, 11, 4)) == 10  # Fri

    # test many weeks
    start_dt = datetime(2022, 9, 29)
    for wks_offset in range(50):
        true_wk = wks_offset + 1 + 4
        assert wkNbr(start_dt + timedelta(weeks=wks_offset)) == true_wk
        assert wkNbr(start_dt + timedelta(weeks=wks_offset, days=1)) == true_wk
        assert wkNbr(start_dt + timedelta(weeks=wks_offset, days=2)) == true_wk
        assert wkNbr(start_dt + timedelta(weeks=wks_offset, days=3)) == true_wk
        assert wkNbr(start_dt + timedelta(weeks=wks_offset, days=4)) == true_wk
        assert wkNbr(start_dt + timedelta(weeks=wks_offset, days=5)) == true_wk
        assert wkNbr(start_dt + timedelta(weeks=wks_offset, days=6)) == true_wk

    # test extremes
    assert wkNbr(datetime(2000, 1, 1)) == -1
    assert wkNbr(datetime(2022, 6, 14)) == -1
    assert wkNbr(datetime(2022, 6, 15)) == -1
    assert 50 < wkNbr(datetime(2030, 1, 1)) < 10000
    assert 50 < wkNbr(datetime(2040, 1, 1)) < 10000


@enforce_types
def test_calcDcvMultiplier():
    mult = calcrewards.calcDcvMultiplier
    assert mult(-10) == np.inf
    assert mult(-1) == np.inf
    assert mult(0) == np.inf
    assert mult(1) == np.inf
    assert mult(8) == np.inf
    assert mult(9) == 1.0
    assert mult(10) == pytest.approx(0.951, 0.001)
    assert mult(11) == pytest.approx(0.903, 0.001)
    assert mult(12) == pytest.approx(0.854, 0.001)
    assert mult(20) == pytest.approx(0.4665, 0.001)
    assert mult(27) == pytest.approx(0.127, 0.001)
    assert mult(28) == pytest.approx(0.0785, 0.001)
    assert mult(29) == 0.03
    assert mult(30) == 0.03
    assert mult(31) == 0.03
    assert mult(100) == 0.03
    assert mult(10000) == 0.03


@enforce_types
def test_boundRewardsByDcv():
    boundRew = calcrewards.boundRewardsByDcv
    mult = calcrewards.calcDcvMultiplier

    # week 1
    # args: (rewards_OCEAN, DCV_OCEAN, DF_week)
    assert boundRew(100.0, 0.0, 1) == 100.0
    assert boundRew(100.0, 1e9, 1) == 100.0

    # week 8
    assert boundRew(100.0, 0.0, 8) == 100.0
    assert boundRew(100.0, 1e9, 8) == 100.0

    # week 9
    assert boundRew(100.0, 0.0, 9) == 0.0
    assert boundRew(100.0, 50.0, 9) == 50.0
    assert boundRew(100.0, 100.0, 9) == 100.0
    assert boundRew(100.0, 1e9, 9) == 100.0

    # week 10
    assert boundRew(100.0, 0.0, 10) == 0.0
    assert boundRew(100.0, 50.0, 10) == mult(10) * 50.0
    assert boundRew(100.0, 100.0, 10) == mult(10) * 100.0
    assert boundRew(100.0, 1e9, 10) == 100.0

    # week 28
    assert boundRew(100.0, 0.0, 28) == 0.0
    assert boundRew(100.0, 50.0, 28) == mult(28) * 50.0
    assert boundRew(100.0, 100.0, 28) == mult(28) * 100.0
    assert boundRew(100.0, 1e9, 28) == 100.0

    # week 29
    assert boundRew(100.0, 0.0, 29) == 0.0
    assert boundRew(100.0, 50.0, 29) == mult(29) * 50.0
    assert boundRew(100.0, 100.0, 29) == mult(29) * 100.0
    assert boundRew(100.0, 1e9, 29) == 100.0

    # week 100
    assert boundRew(100.0, 0.0, 100) == 0.0
    assert boundRew(100.0, 50.0, 100) == mult(100) * 50.0
    assert boundRew(100.0, 100.0, 100) == mult(100) * 100.0
    assert boundRew(100.0, 1e9, 100) == 100.0


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
