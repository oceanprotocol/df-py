from datetime import datetime, timedelta
from typing import Dict, Tuple, Union

from enforce_typing import enforce_types
import numpy as np
import pytest
from pytest import approx

from util import calcrewards, networkutil, cleancase as cc, constants, tousd
from util.calcrewards import TARGET_WPY, _rankBasedAllocate
from util.constants import ZERO_ADDRESS
from util.base18 import fromBase18

# for shorter lines
RATES = {"OCEAN": 0.5, "H2O": 1.6, "PSDN": 0.01}
C1, C2, C3 = 7, 137, 1285  # chainIDs
NA, NB, NC = "0xnfta_addr", "0xnftb_addr", "0xnftc_addr"
LP1, LP2, LP3, LP4 = "0xlp1_addr", "0xlp2_addr", "0xlp3_addr", "0xlp4_addr"
OCN_SYMB, H2O_SYMB = "OCEAN", "H2O"
OCN_ADDR, H2O_ADDR = "0xocean", "0xh2o"
OCN_ADDR2, H2O_ADDR2 = "0xocean2", "0xh2o2"
SYMBOLS = {
    C1: {OCN_ADDR: OCN_SYMB, H2O_ADDR: H2O_SYMB},
    C2: {OCN_ADDR2: OCN_SYMB, H2O_ADDR2: H2O_SYMB},
}
APPROVED_TOKEN_ADDRS = {C1: [OCN_ADDR, H2O_ADDR], C2: [OCN_ADDR2, H2O_ADDR2]}


@enforce_types
def test_simple():
    stakes = {C1: {NA: {LP1: 1000.0}}}
    nftvols = {C1: {OCN_ADDR: {NA: 1.0}}}
    OCEAN_avail = 10.0

    rewardsperlp, rewardsinfo = _calcRewards(stakes, nftvols, OCEAN_avail)
    assert rewardsperlp == {C1: {LP1: 10.0}}
    assert rewardsinfo == {C1: {NA: {LP1: 10}}}

    # test helper - just C1
    rewardsperlp, rewardsinfo = _calcRewardsC1(stakes, nftvols, OCEAN_avail)
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
    nftvols = {C1: {OCN_ADDR: {NA: 40.0}, H2O_ADDR: {NB: 12.5}}}

    OCEAN_avail = 10.0
    rewardsperlp, rewardsinfo = _calcRewardsC1(stakes, nftvols, OCEAN_avail)

    NA_RF_USD = 0.5 * 40.0 * 0.5
    NB_RF_USD = 0.5 * 12.5 * 1.6
    NA_amt = NA_RF_USD / (NA_RF_USD + NB_RF_USD) * 10.0
    NB_amt = NB_RF_USD / (NA_RF_USD + NB_RF_USD) * 10.0

    assert rewardsperlp == {LP1: 10.0}
    assert rewardsinfo == {NA: {LP1: NA_amt}, NB: {LP1: NB_amt}}


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

    OCEAN_avail = 20.0

    rewardsperlp, rewardsinfo = _calcRewards(
        stakes, nftvols, OCEAN_avail, symbols=symbols
    )

    assert rewardsperlp == target_rewardsperlp
    assert rewardsinfo == target_rewardsinfo

    # now, make it so that Ocean token in C2 is MOCEAN
    symbols[C2][OCN_ADDR2] = "MOCEAN"
    rewardsperlp, rewardsinfo = _calcRewards(
        stakes, nftvols, OCEAN_avail, symbols=symbols
    )

    assert rewardsperlp == {C1: {LP1: 20.0}}  # it completely ignores C2's MOCEAN ...
    assert rewardsinfo == {
        C1: {NA: {LP1: 20.0}}
    }  # ...but of course we don't want that...

    # ... so here's the intervention needed!
    rates = RATES.copy()
    rates["MOCEAN"] = rates["OCEAN"]

    rewardsperlp, rewardsinfo = _calcRewards(
        stakes, nftvols, OCEAN_avail, rates=rates, symbols=symbols
    )

    # now the rewards should line up as expected
    assert rewardsperlp == target_rewardsperlp
    assert rewardsinfo == target_rewardsinfo


@enforce_types
def test_two_lps_simple():
    stakes = {C1: {NA: {LP1: 100e3, LP2: 100e3}}}
    nftvols = {C1: {OCN_ADDR: {NA: 1.0}}}

    OCEAN_avail = 10.0
    rewardsperlp, rewardsinfo = _calcRewardsC1(stakes, nftvols, OCEAN_avail)

    assert sum(rewardsperlp.values()) == pytest.approx(10.0, 0.01)
    assert sum(rewardsinfo[NA].values()) == pytest.approx(10.0, 0.01)
    assert rewardsperlp == {LP1: 5.0, LP2: 5.0}
    assert rewardsinfo == {NA: {LP1: 5.0, LP2: 5.0}}


@enforce_types
def test_two_lps_one_with_negligible_stake():
    stakes = {C1: {NA: {LP1: 10e3, LP2: 1e-14 * 10e3}}}
    nftvols = {C1: {OCN_ADDR: {NA: 1.0}}}
    OCEAN_avail = 10.0

    rewardsperlp, rewardsinfo = _calcRewardsC1(stakes, nftvols, OCEAN_avail)

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
    nftvols = {C1: {OCN_ADDR: {NA: 1.0}}}  # NA has volume, but not NB
    OCEAN_avail = 10.0

    rewardsperlp, rewardsinfo = _calcRewardsC1(stakes, nftvols, OCEAN_avail)

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
    nftvols = {C1: {OCN_ADDR: {NA: 1.0, NB: 1.0}}}  # NA & NB both have volume
    OCEAN_avail = 10.0

    rewardsperlp, rewardsinfo = _calcRewardsC1(stakes, nftvols, OCEAN_avail)

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
def test_two_LPs__one_NFT__one_LP_created():
    # LP1 created NA, so it gets 2x equivalent stake on that
    stakes = {C1: {NA: {LP1: 50e3, LP2: 100e3}}}
    nftvols = {C1: {OCN_ADDR: {NA: 1.0}}}
    owners = {C1: {NA: LP1}}

    OCEAN_avail = 10.0
    rewardsperlp, rewardsinfo = _calcRewardsC1(
        stakes, nftvols, OCEAN_avail, owners=owners, do_pubrewards=True
    )

    assert sum(rewardsperlp.values()) == pytest.approx(10.0, 0.01)
    assert sum(rewardsinfo[NA].values()) == pytest.approx(10.0, 0.01)
    assert rewardsperlp == {LP1: 5.0, LP2: 5.0}
    assert rewardsinfo == {NA: {LP1: 5.0, LP2: 5.0}}


@enforce_types
def test_two_LPs__two_NFTs__one_LP_created_one_NFT():
    # LP1 created NA, so it gets 2x equivalent stake on NA (but not NB)
    stakes = {C1: {NA: {LP1: 50e3, LP2: 100e3}, NB: {LP1: 100e3, LP2: 100e3}}}
    nftvols = {C1: {OCN_ADDR: {NA: 1.0, NB: 1.0}}}
    owners = {C1: {NA: LP1, NB: ZERO_ADDRESS}}

    OCEAN_avail = 10.0
    rewardsperlp, rewardsinfo = _calcRewardsC1(
        stakes, nftvols, OCEAN_avail, owners=owners, do_pubrewards=True
    )

    assert sum(rewardsperlp.values()) == pytest.approx(10.0, 0.01)
    assert sum(rewardsinfo[NA].values()) == pytest.approx(5.0, 0.01)
    assert rewardsperlp == {LP1: 5.0, LP2: 5.0}
    assert rewardsinfo == {NA: {LP1: 2.5, LP2: 2.5}, NB: {LP1: 2.5, LP2: 2.5}}


@enforce_types
def test_two_LPs__two_NFTs__two_LPs_created():
    # LP1 created NA, LP2 created NB, they each get 2x equivalent stake
    stakes = {C1: {NA: {LP1: 50e3, LP2: 100e3}, NB: {LP1: 100e3, LP2: 50e3}}}
    nftvols = {C1: {OCN_ADDR: {NA: 1.0, NB: 1.0}}}
    owners = {C1: {NA: LP1, NB: LP2}}

    OCEAN_avail = 10.0
    rewardsperlp, rewardsinfo = _calcRewardsC1(
        stakes, nftvols, OCEAN_avail, owners=owners, do_pubrewards=True
    )

    assert sum(rewardsperlp.values()) == pytest.approx(10.0, 0.01)
    assert sum(rewardsinfo[NA].values()) == pytest.approx(5.0, 0.01)
    assert rewardsperlp == {LP1: 5.0, LP2: 5.0}
    assert rewardsinfo == {NA: {LP1: 2.5, LP2: 2.5}, NB: {LP1: 2.5, LP2: 2.5}}


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
    OCEAN_avail = 10.0

    # tests
    rewardsperlp, rewardsinfo = _calcRewards(stakes2a, nftvols, OCEAN_avail)
    assert target_rewardsperlp == rewardsperlp
    assert target_rewardsinfo == rewardsinfo

    rewardsperlp, _ = _calcRewards(stakes2b, nftvols, OCEAN_avail)
    assert target_rewardsperlp == rewardsperlp
    assert target_rewardsinfo == rewardsinfo

    rewardsperlp, _ = _calcRewards(stakes2c, nftvols, OCEAN_avail)
    assert target_rewardsperlp == rewardsperlp
    assert target_rewardsinfo == rewardsinfo

    rewardsperlp, _ = _calcRewards(stakes, nftvols2a, OCEAN_avail)
    assert target_rewardsperlp == rewardsperlp
    assert target_rewardsinfo == rewardsinfo

    rewardsperlp, _ = _calcRewards(stakes, nftvols2b, OCEAN_avail)
    assert target_rewardsperlp == rewardsperlp
    assert target_rewardsinfo == rewardsinfo

    rewardsperlp, _ = _calcRewards(stakes, nftvols, OCEAN_avail, rates=rates2)
    assert target_rewardsperlp == rewardsperlp
    assert target_rewardsinfo == rewardsinfo


def test_calcrewards_math():
    ## update this test when the reward function is changed
    stakes = {C1: {NA: {LP1: 1.0e6, LP2: 9.0e6}, NB: {LP3: 10.0e6, LP4: 90.0e6}}}
    nftvols = {C1: {OCN_ADDR: {NA: 0.5e6, NB: 0.5e6}}}
    OCEAN_avail = 5000.0

    rewardsperlp, _ = _calcRewardsC1(stakes, nftvols, OCEAN_avail)

    assert sum(rewardsperlp.values()) == pytest.approx(OCEAN_avail, 0.01)

    assert rewardsperlp[LP1] == pytest.approx(250.0, 0.01)
    assert rewardsperlp[LP2] == pytest.approx(2250.0, 0.01)
    assert rewardsperlp[LP3] == pytest.approx(250.0, 0.01)
    assert rewardsperlp[LP4] == pytest.approx(2250.0, 0.01)


@enforce_types
def test_bound_APY_one_nft():
    stakes = {C1: {NA: {LP1: 1.0}}}
    nftvols = {C1: {OCN_ADDR: {NA: 1.0}}}
    OCEAN_avail = 10000.0

    rewardsperlp, rewardsinfo = _calcRewardsC1(stakes, nftvols, OCEAN_avail)

    assert rewardsperlp == {LP1: 1.0 * TARGET_WPY}
    assert rewardsinfo == {NA: {LP1: 1.0 * TARGET_WPY}}


@enforce_types
def test_bound_APY_one_LP__high_stake__two_nfts():
    stakes = {C1: {NA: {LP1: 1e6}, NB: {LP1: 1e6}}}
    nftvols = {C1: {OCN_ADDR: {NA: 1.0, NB: 1.0}}}
    OCEAN_avail = 1000.0

    rewardsperlp, rewardsinfo = _calcRewardsC1(stakes, nftvols, OCEAN_avail)

    # ensure that total rewards given doesn't exceed OCEAN_avail
    assert rewardsperlp == {LP1: 1000.0}
    assert rewardsinfo == {NA: {LP1: 500.0}, NB: {LP1: 500.0}}


@enforce_types
def test_bound_APY_two_nfts__equal_low_stake__equal_low_DCV():
    stakes = {C1: {NA: {LP1: 5.0}, NB: {LP2: 5.0}}}
    nftvols = {C1: {OCN_ADDR: {NA: 1.0, NB: 1.0}}}
    OCEAN_avail = 10000.0

    rewardsperlp, rewardsinfo = _calcRewardsC1(stakes, nftvols, OCEAN_avail)

    assert rewardsperlp == {LP1: 5.0 * TARGET_WPY, LP2: 5.0 * TARGET_WPY}
    assert rewardsinfo == {NA: {LP1: 5.0 * TARGET_WPY}, NB: {LP2: 5.0 * TARGET_WPY}}


@enforce_types
def test_bound_APY_two_nfts__both_low_stake__one_nft_dominates_stake():
    stakes = {C1: {NA: {LP1: 5.0}, NB: {LP2: 20000.0}}}
    nftvols = {C1: {OCN_ADDR: {NA: 1.0, NB: 1.0}}}
    OCEAN_avail = 10000.0

    rewardsperlp, rewardsinfo = _calcRewardsC1(stakes, nftvols, OCEAN_avail)

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
    OCEAN_avail = 10000.0

    rewardsperlp, rewardsinfo = _calcRewardsC1(stakes, nftvols, OCEAN_avail)

    # LP1 and LP2 get same amount - they're both bounded because both have low stake
    # Critically, LP2 doesn't swamp LP1 just because LP2's stake * DCV is way higher
    assert rewardsperlp == {LP1: 5.0 * TARGET_WPY, LP2: 5.0 * TARGET_WPY}
    assert rewardsinfo == {NA: {LP1: 5.0 * TARGET_WPY}, NB: {LP2: 5.0 * TARGET_WPY}}


@enforce_types
def test_bound_APY_two_nfts__high_stake__one_nft_dominates_DCV():
    stakes = {C1: {NA: {LP1: 1e6}, NB: {LP2: 1e6}}}
    nftvols = {C1: {OCN_ADDR: {NA: 1.0, NB: 9999.0}}}
    OCEAN_avail = 10000.0

    rewardsperlp, rewardsinfo = _calcRewardsC1(stakes, nftvols, OCEAN_avail)

    # LP2 reward swamps LP1 because LP2's stake * DCV is way higher
    assert rewardsperlp == {LP1: 1.0, LP2: 9999.0}
    assert rewardsinfo == {NA: {LP1: 1.0}, NB: {LP2: 9999.0}}


@enforce_types
def test_bound_by_DCV_one_nft():
    DCV_OCEAN = 100.0
    DCV_USD = DCV_OCEAN / RATES["OCEAN"]

    stakes = {C1: {NA: {LP1: 1e6}}}
    nftvols = {C1: {OCN_ADDR: {NA: DCV_USD}}}
    OCEAN_avail = 10000.0

    rewardsperlp, rewardsinfo = _calcRewardsC1(
        stakes, nftvols, OCEAN_avail, DCV_multiplier=1.0
    )
    assert rewardsperlp == {LP1: 100.0}
    assert rewardsinfo == {NA: {LP1: 100.0}}

    rewardsperlp, rewardsinfo = _calcRewardsC1(
        stakes, nftvols, OCEAN_avail, DCV_multiplier=0.5
    )
    assert rewardsperlp == {LP1: 50.0}
    assert rewardsinfo == {NA: {LP1: 50.0}}


@enforce_types
def test_divide_by_zero():
    stakes = {C1: {NA: {LP1: 10000.0}, NB: {LP2: 10000.0}}}
    nftvols = {C1: {OCN_ADDR: {LP1: 0, LP2: 0}}}
    OCEAN_avail = 10000.0

    rewardsperlp, _ = _calcRewardsC1(stakes, nftvols, OCEAN_avail)

    # Should return empty dict because LP1 and LP2 have zero volume
    assert rewardsperlp == {}


# ========================================================================
# Tests around bounding rewards by DCV


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
    assert mult(29) == 0.001
    assert mult(30) == 0.001
    assert mult(31) == 0.001
    assert mult(100) == 0.001
    assert mult(10000) == 0.001


# ========================================================================
# Test rank-based allocate -- end-to-end with calcRewards()
@enforce_types
def test_rank_1_NFT():
    stakes = {C1: {NA: {LP1: 1000.0}}}
    nftvols = {C1: {OCN_ADDR: {NA: 1.0}}}
    OCEAN_avail = 10.0

    rew, _ = _calcRewardsC1(stakes, nftvols, OCEAN_avail, do_rank=True)
    assert rew == {LP1: 10.0}


@enforce_types
def test_rank_3_NFTs():
    stakes = {C1: {NA: {LP1: 1000.0}, NB: {LP2: 1000.0}, NC: {LP3: 1000.0}}}
    OCEAN_avail = 10.0

    # equal volumes
    nftvols = {C1: {OCN_ADDR: {NA: 1.0, NB: 1.0, NC: 1.0}}}
    rew, _ = _calcRewardsC1(stakes, nftvols, OCEAN_avail, do_rank=True)
    assert sorted(rew.keys()) == [LP1, LP2, LP3]
    assert sum(rew.values()) == pytest.approx(10.0, 0.01)
    for LP in [LP1, LP2, LP3]:
        assert rew[LP] == pytest.approx(10.0 / 3.0)

    # unequal volumes
    nftvols = {C1: {OCN_ADDR: {NA: 1.0, NB: 0.002, NC: 0.001}}}
    rew, _ = _calcRewardsC1(stakes, nftvols, OCEAN_avail, do_rank=True)
    assert sorted(rew.keys()) == [LP1, LP2, LP3]
    assert sum(rew.values()) == pytest.approx(10.0, 0.01)
    assert rew[LP1] > rew[LP2] > rew[LP3], rew
    assert rew[LP1] > 3.33, rew
    assert rew[LP2] > 1.0, rew  # if it was pro-rata it would have been << 1.0
    assert rew[LP3] > 1.0, rew  # ""


@enforce_types
def test_rank_10_NFTs():
    _test_rank_N_NFTs(10)


@enforce_types
def test_rank_200_NFTs():
    _test_rank_N_NFTs(200)


@enforce_types
def _test_rank_N_NFTs(N: int):
    OCEAN_avail = 10.0

    # equal volumes
    (_, LP_addrs, stakes, nftvols) = _rank_testvals(N, equal_vol=True)
    rew, _ = _calcRewardsC1(stakes, nftvols, OCEAN_avail, do_rank=True)
    assert len(rew) == N
    assert LP_addrs == sorted(rew.keys())
    assert sum(rew.values()) == pytest.approx(10.0, 0.01)
    assert min(rew.values()) == max(rew.values())

    # unequal volumes
    (_, LP_addrs, stakes, nftvols) = _rank_testvals(N, equal_vol=False)
    rew, _ = _calcRewardsC1(stakes, nftvols, OCEAN_avail, do_rank=True)
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


# ========================================================================
# Test rank-based allocate -- key building block rankBasedAllocate()


@enforce_types
def test_rankBasedAllocate_zerovols():
    V_USD = np.array([32.0, 0.0, 15.0], dtype=float)
    with pytest.raises(ValueError):
        _rankBasedAllocate(V_USD)


@enforce_types
def test_rankBasedAllocate_0():
    V_USD = np.array([], dtype=float)
    p = _rankBasedAllocate(V_USD)
    target_p = np.array([], dtype=float)
    np.testing.assert_allclose(p, target_p)


@enforce_types
def test_rankBasedAllocate_1():
    V_USD = np.array([32.0], dtype=float)
    p = _rankBasedAllocate(V_USD)
    target_p = np.array([1.0], dtype=float)
    np.testing.assert_allclose(p, target_p)


@enforce_types
def test_rankBasedAllocate_3_simple():
    V_USD = np.array([10.0, 99.0, 3.0], dtype=float)
    p = _rankBasedAllocate(V_USD, rank_scale_op="LIN")
    target_p = np.array([2.0 / 6.0, 3.0 / 6.0, 1.0 / 6.0], dtype=float)
    np.testing.assert_allclose(p, target_p)


@enforce_types
@pytest.mark.parametrize("op", ["LIN", "POW2", "POW4", "LOG", "SQRT"])
def test_rankBasedAllocate_3_exact(op):
    V_USD = np.array([10.0, 99.0, 3.0], dtype=float)

    (p, ranks, max_N, allocs, I) = _rankBasedAllocate(
        V_USD, max_n_rank_assets=100, rank_scale_op=op, return_info=True
    )

    target_max_N = 3
    target_ranks = [2, 1, 3]
    target_I = [0, 1, 2]

    assert max_N == target_max_N
    assert min(allocs) > 0, f"had an alloc=0; op={op}, allocs={allocs}"
    assert min(p) > 0, f"had a p=0; op={op}, allocs={allocs}, p={p}"
    np.testing.assert_allclose(ranks, np.array(target_ranks, dtype=float))
    np.testing.assert_allclose(I, np.array(target_I, dtype=float))

    if op == "LIN":
        target_allocs = [2.0, 3.0, 1.0]
        target_p = np.array([2.0 / 6.0, 3.0 / 6.0, 1.0 / 6.0], dtype=float)
    elif op == "LOG":
        target_allocs = [0.352183, 0.653213, 0.176091]
        target_p = [0.298084, 0.552874, 0.149042]
    else:
        return

    target_allocs = np.array(target_allocs, dtype=float)
    target_p = np.array(target_p, dtype=float)

    np.testing.assert_allclose(allocs, target_allocs, rtol=1e-3)
    np.testing.assert_allclose(p, target_p, rtol=1e-3)


@enforce_types
def test_rankBasedAllocate_20():
    V_USD = 1000.0 * np.random.rand(20)
    p = _rankBasedAllocate(V_USD)
    assert len(p) == 20
    assert sum(p) == pytest.approx(1.0)


@enforce_types
def test_rankBasedAllocate_1000():
    V_USD = 1000.0 * np.random.rand(1000)
    p = _rankBasedAllocate(V_USD)
    assert len(p) == 1000
    assert sum(p) == pytest.approx(1.0)


@enforce_types
@pytest.mark.skip(reason="only unskip this when doing manual tuning")
def test_plot_ranks():
    # This function is for manual exploration around shapes of the rank curve
    # To use it:
    # 1. in this file, right above: comment out "pytest.mark.skip" line
    # 2. in console: pip install matplotlib
    # 3. in this file, right below: change any "settable values"
    # 4. in console: pytest util/test/test_calcrewards.py::test_plot_ranks

    # settable values
    save_or_show = "save"  # "save" or "show"
    max_ns = [20, 50, 100]  # example list: [20, 50, 100]
    ops = [
        "LIN",
        "POW2",
        "POW4",
        "LOG",
        "SQRT",
    ]  # full list: ["LIN", "POW2", "POW4", "LOG", "SQRT"]

    # go!
    for max_n in max_ns:
        for op in ops:
            _plot_ranks(save_or_show, max_n, op)


@enforce_types
def _plot_ranks(save_or_show, max_n_rank_assets, rank_scale_op):
    # pylint: disable=unused-variable, import-outside-toplevel

    import matplotlib
    import matplotlib.pyplot as plt

    N = 120
    V_USD = np.arange(N, 0, -1)  # N, N-1, ..., 2, 1. Makes ranking obvious!

    p = _rankBasedAllocate(
        V_USD, max_n_rank_assets=max_n_rank_assets, rank_scale_op=rank_scale_op
    )

    if save_or_show == "save":
        fontsize = 6
        linewidth_m = 0.2
    elif save_or_show == "show":
        fontsize = 25
        linewidth_m = 1.0
    else:
        raise ValueError(save_or_show)

    matplotlib.rcParams.update({"font.size": fontsize})

    _, ax1 = plt.subplots()
    ax2 = ax1.twinx()

    x = np.arange(1, N + 1)
    ax1.bar(x, 100.0 * p)
    ax1.set_xlabel("DCV Rank of data asset (1=highest)")
    ax1.set_ylabel("% of OCEAN to data asset", color="b")

    ax2.plot(x, np.cumsum(100.0 * p), "g-", linewidth=3.5 * linewidth_m)
    ax2.set_ylabel("Cumulative % of OCEAN to assets", color="g")

    plt.title(
        "% of OCEAN to data asset vs rank"
        f". max_n_rank_assets={max_n_rank_assets}"
        f", rank_scale_op={rank_scale_op}"
    )

    # Show the major grid and style it slightly.
    ax1.grid(
        axis="y",
        which="major",
        color="#DDDDDD",
        linewidth=2.5 * linewidth_m,
        linestyle="-",
    )

    xticks = [1] + list(np.arange(10, N + 1, 5))
    xlabels = [str(xtick) for xtick in xticks]
    plt.xticks(xticks, xlabels)

    if save_or_show == "save":
        fname = f"max-{max_n_rank_assets:03d}_scale-{rank_scale_op}.png"
        plt.savefig(fname, dpi=300)
        print(f"Saved {fname}")
    elif save_or_show == "show":
        mng = plt.get_current_fig_manager()
        mng.resize(*mng.window.maxsize())
        plt.show()
    else:
        raise ValueError(save_or_show)


# ========================================================================
# Test helper functions found in calcrewards


@enforce_types
def test_getNftAddrs():
    nftvols_USD = {C1: {NA: 1.0, NB: 1.0}, C2: {NC: 1.0}}
    nft_addrs = calcrewards._getNftAddrs(nftvols_USD)
    assert isinstance(nft_addrs, list)
    assert sorted(nft_addrs) == sorted([NA, NB, NC])


@enforce_types
def test_getLpAddrs():
    stakes = {
        C1: {
            NA: {LP1: 5.0, LP2: 1.0},
            NB: {LP1: 5.0, LP3: 1.0},
        },
        C2: {
            NA: {LP1: 5.0},
            NC: {LP4: 1.0},
        },
    }
    LP_addrs = calcrewards._getLpAddrs(stakes)
    assert isinstance(LP_addrs, list)
    assert sorted(LP_addrs) == sorted([LP1, LP2, LP3, LP4])


@enforce_types
def test_flattenRewards():
    rewards = {
        C1: {
            LP1: 100.0,
            LP2: 200.0,
        },
        C2: {
            LP1: 300.0,
        },
        C3: {
            LP1: 500.0,
            LP2: 600.0,
            LP3: 700.0,
        },
    }

    flat_rewards = calcrewards.flattenRewards(rewards)
    assert flat_rewards == {
        LP1: 100.0 + 300.0 + 500.0,
        LP2: 200.0 + 600.0,
        LP3: 700.0,
    }


@pytest.mark.parametrize(
    "test_input, expected_output",
    [
        (datetime(2023, 3, 16), 120670.89),
        (datetime(2023, 4, 16), 120670.89),
        (datetime(2024, 3, 8), 120670.89),
        (datetime(2024, 3, 15), 301677.226),
        (datetime(2024, 9, 8), 301677.226),
        (datetime(2024, 9, 15), 603354.45),
        (datetime(2025, 3, 8), 603354.45),
        (datetime(2025, 3, 15), 1206708.9),
    ],
)
def test_getRewardAmountForWeekWei(test_input, expected_output):
    networkutil.connect(networkutil.DEV_CHAINID)
    assert fromBase18(calcrewards.getRewardAmountForWeekWei(test_input)) == approx(
        expected_output
    )


# ========================================================================
# Helpers to keep function calls compact, and return vals compact.


@enforce_types
def _calcRewardsC1(
    stakes: Dict[int, Dict[str, Dict[str, float]]],
    nftvols: Dict[int, Dict[str, Dict[str, float]]],
    OCEAN_avail: float,
    symbols: Dict[int, Dict[str, str]] = SYMBOLS,
    rates: Dict[str, float] = RATES,
    owners=None,
    DCV_multiplier: float = np.inf,
    do_pubrewards: bool = False,
    do_rank: bool = False,
):
    rewardsperlp, rewardsinfo = _calcRewards(
        stakes,
        nftvols,
        OCEAN_avail,
        symbols,
        rates,
        owners,
        DCV_multiplier,
        do_pubrewards,
        do_rank,
    )
    rewardsperlp = {} if not rewardsperlp else rewardsperlp[C1]
    rewardsinfo = {} if not rewardsinfo else rewardsinfo[C1]
    return rewardsperlp, rewardsinfo


@enforce_types
def _calcRewards(
    stakes: Dict[int, Dict[str, Dict[str, float]]],
    nftvols: Dict[int, Dict[str, Dict[str, float]]],
    OCEAN_avail: float,
    symbols: Dict[int, Dict[str, str]] = SYMBOLS,
    rates: Dict[str, float] = RATES,
    owners=None,
    DCV_multiplier: float = np.inf,
    do_pubrewards: bool = False,
    do_rank: bool = False,
):
    """Helper. Fills in SYMBOLS, RATES, and DCV_multiplier for compactness"""
    if owners is None:
        owners = _nullOwners(stakes, nftvols, symbols, rates)

    return calcrewards.calcRewards(
        stakes,
        nftvols,
        owners,
        symbols,
        rates,
        DCV_multiplier,
        OCEAN_avail,
        do_pubrewards,
        do_rank,
    )


@enforce_types
def _nullOwners(
    stakes,
    nftvols,
    symbols,
    rates,
) -> Dict[int, Dict[str, Union[str, None]]]:
    """@return - owners -- dict of [chainID][nft_addr] : ZERO_ADDRESS"""
    stakes, nftvols, symbols, rates = (
        cc.modStakes(stakes),
        cc.modNFTvols(nftvols),
        cc.modSymbols(symbols),
        cc.modRates(rates),
    )
    nftvols_USD = tousd.nftvolsToUsd(nftvols, symbols, rates)
    chain_nft_tups = calcrewards._getChainNftTups(stakes, nftvols_USD)

    owners: Dict[int, Dict[str, Union[str, None]]] = {}
    for chainID, nft_addr in chain_nft_tups:
        if chainID not in owners:
            owners[chainID] = {}
        owners[chainID][nft_addr] = ZERO_ADDRESS
    return owners
