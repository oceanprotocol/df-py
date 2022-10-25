from enforce_typing import enforce_types
import pytest
from pytest import approx

from util import cleancase
from util.calcrewards import calcRewards, TARGET_WPY

# for shorter lines
RATES = {"OCEAN": 0.5, "H2O": 1.6, "PSDN": 0.01}
C1, C2 = 7, 137
NA, NB = "0xnfta_addr", "0xnftb_addr"
ST1, ST2, ST3 = "0xst1_addr", "0xst2_addr", "0xst3_addr"
OCN_SYMB, H2O_SYMB = "OCEAN", "H2O"
OCN_ADDR, H2O_ADDR = "0xocean", "0xh2o"
SYMBOLS = {
    C1: {OCN_ADDR: OCN_SYMB, H2O_ADDR: H2O_SYMB},
    C2: {"0xocean2": "OCEAN", "Oxh2o2": "H2O"},
}
APPROVED_TOKEN_ADDRS = {C1: [OCN_ADDR, H2O_ADDR], C2: ["0xocean2", "Oxh2o2"]}


@enforce_types
def test_simple():
    stakes = {C1: {NA: {ST1: 1000.0}}}
    vebals = {ST1: 1000.0}
    nftvols = {C1: {OCN_ADDR: {NA: 1.0}}}

    rewards_avail = 10.0 #in OCEAN

    rewardsperlp, rewardsinfo = _calcRewards(stakes, nftvols, rewards_avail)
    assert rewardsperlp == {C1: {ST1: 10.0}}
    assert rewardsinfo == {C1: {NA: {ST1: 10}}}

    # test helper - just C1
    rewardsperlp, rewardsinfo = _calcRewardsC1(stakes, nftvols, rewards_avail)
    assert rewardsperlp == {ST1: 10.0}
    assert rewardsinfo == {NA: {ST1: 10}}


@enforce_types
def test_two_basetokens_OCEAN_and_H2O():
    stakes = {
        C1: {
            NA: {ST1: 5000.0},
            NB: {ST1: 5000.0},
        }
    }
    nftvols = {
        C1: {OCN_ADDR: {NA: 40.0}, H2O_ADDR: {NB: 12.5}}  # vol in units of OCEAN
    }  # vol in units of H2O

    rewards_avail = 10.0 # in OCEAN
    rewardsperlp, rewardsinfo = _calcRewardsC1(stakes, nftvols, rewards_avail)

    NA_RF_USD = 0.5 * 40.0 * 0.5
    NB_RF_USD = 0.5 * 12.5 * 1.6
    NA_amt = NA_RF_USD / (NA_RF_USD + NB_RF_USD) * 10.0
    NB_amt = NB_RF_USD / (NA_RF_USD + NB_RF_USD) * 10.0

    assert rewardsperlp == {ST1: 10.0}
    assert rewardsinfo == {NA: {ST1: NA_amt}, NB: {ST1: NB_amt}}


#===================== FIXME FROM HERE ON

    
@enforce_types
def test_two_chains():
    # first cut: symbols are the same
    allocations = {
        C1: {NA: {ST1: 0.5}},
        C2: {NB: {ST1: 0.5}},
    }
    vebals = {ST1: 100000.0}
    nftvols = {C1: {OCN_ADDR: {NA: 1.0}}, C2: {"0xocean2": {NB: 1.0}}}
    symbols = {
        C1: {OCN_ADDR: OCN_SYMB, H2O_ADDR: H2O_SYMB},
        C2: {"0xocean2": "OCEAN", "Oxh2o2": "H2O"},
    }

    target_rewardsperlp = {C1: {ST1: 10.0}, C2: {ST1: 10.0}}
    target_rewardsinfo = {C1: {NA: {ST1: 10.0}}, C2: {NB: {ST1: 10.0}}}

    rewards_avail_OCEAN = 20.0

    rewardsperlp, rewardsinfo = _calcRewards(
        allocations, vebals, nftvols, rewards_avail_OCEAN, symbols=symbols
    )

    assert rewardsperlp == target_rewardsperlp
    assert rewardsinfo == target_rewardsinfo

    # now, make it so that Ocean token in C2 is MOCEAN
    symbols[C2]["0xocean2"] = "MOCEAN"
    rewardsperlp, rewardsinfo = _calcRewards(
        allocations, vebals, nftvols, rewards_avail_OCEAN, symbols=symbols
    )

    assert rewardsperlp == {C1: {ST1: 20.0}}  # it completely ignores C2's MOCEAN ...
    assert rewardsinfo == {
        C1: {NA: {ST1: 20.0}}
    }  # ...but of course we don't want that...

    # ... so here's the intervention needed!
    rates = RATES.copy()
    rates["MOCEAN"] = rates["OCEAN"]

    rewardsperlp, rewardsinfo = _calcRewards(
        allocations, vebals, nftvols, rewards_avail_OCEAN, rates=rates, symbols=symbols
    )

    # now the rewards should line up as expected
    assert rewardsperlp == target_rewardsperlp
    assert rewardsinfo == target_rewardsinfo


@enforce_types
def test_two_lps_simple():
    allocations = {C1: {NA: {ST1: 1.0, ST2: 1.0}}}
    vebals = {ST1: 100000.0, ST2: 100000.0}
    nftvols = {C1: {OCN_ADDR: {NA: 1.0}}}

    rewards_avail_OCEAN = 10.0
    rewardsperlp, rewardsinfo = _calcRewardsC1(
        allocations, vebals, nftvols, rewards_avail_OCEAN
    )

    assert sum(rewardsperlp.values()) == pytest.approx(10.0, 0.01)
    assert sum(rewardsinfo[NA].values()) == pytest.approx(10.0, 0.01)
    assert rewardsperlp == {ST1: 5.0, ST2: 5.0}
    assert rewardsinfo == {NA: {ST1: 5.0, ST2: 5.0}}


@enforce_types
def test_two_lps_one_with_negligible_stake():
    allocations = {C1: {NA: {ST1: 1.0, ST2: 1e-14}}}
    vebals = {ST1: 10000.0, ST2: 10000.0}
    nftvols = {C1: {OCN_ADDR: {NA: 1.0}}}
    rewards_avail_OCEAN = 10.0

    rewardsperlp, rewardsinfo = _calcRewardsC1(
        allocations, vebals, nftvols, rewards_avail_OCEAN
    )

    assert sum(rewardsperlp.values()) == pytest.approx(10.0, 0.01)
    assert sum(rewardsinfo[NA].values()) == pytest.approx(10.0, 0.01)
    assert rewardsperlp == {ST1: 10.0}  # no entry for ST2
    assert rewardsinfo == {NA: {ST1: 10.0}}  # no entry for ST2


@enforce_types
def test_two_nfts_one_with_volume():
    allocations = {
        C1: {
            NA: {ST1: 1.0, ST2: 1.0},
            NB: {ST3: 1.0},
        }
    }
    vebals = {ST1: 10000.0, ST2: 10000.0, ST3: 10000.0}
    nftvols = {C1: {OCN_ADDR: {NA: 1.0}}}  # P1 has volume, but not P2
    rewards_avail_OCEAN = 10.0

    rewardsperlp, rewardsinfo = _calcRewardsC1(
        allocations, vebals, nftvols, rewards_avail_OCEAN
    )

    assert sum(rewardsperlp.values()) == pytest.approx(10.0, 0.01)
    assert min(rewardsperlp.values()) > 0, "shouldn't have entries with 0 rewards"
    assert rewardsperlp == {ST1: 5.0, ST2: 5.0}

    assert sum(rewardsinfo[NA].values()) == pytest.approx(10.0, 0.01)
    assert min(rewardsinfo[NA].values()) > 0, "shouldn't have entries with 0 rewards"
    assert rewardsinfo == {NA: {ST1: 5.0, ST2: 5.0}}


@enforce_types
def test_two_nfts_both_with_volume():
    allocations = {
        C1: {
            NA: {ST1: 0.5, ST2: 1.0},
            NB: {ST1: 0.5, ST3: 1.0},
        }
    }
    vebals = {ST1: 10000.0, ST2: 10000.0, ST3: 10000.0}
    nftvols = {C1: {OCN_ADDR: {NA: 1.0, NB: 1.0}}}  # P1 & P2 both have volume
    rewards_avail_OCEAN = 10.0

    rewardsperlp, rewardsinfo = _calcRewardsC1(
        allocations, vebals, nftvols, rewards_avail_OCEAN
    )

    assert sum(rewardsperlp.values()) == pytest.approx(10.0, 0.01)
    assert rewardsperlp[ST1] == rewardsperlp[ST2]
    assert rewardsperlp[ST1] == rewardsperlp[ST3]
    assert rewardsperlp[ST2] == rewardsperlp[ST3]

    assert sum(rewardsinfo[NA].values()) == pytest.approx(5.0, 0.01)
    assert sum(rewardsinfo[NB].values()) == pytest.approx(5.0, 0.01)
    assert rewardsinfo[NA][ST1] == approx(10 / 3 / 2)
    assert rewardsinfo[NB][ST1] == approx(10 / 3 / 2)
    assert rewardsinfo[NA][ST2] == approx(10 / 3)
    assert rewardsinfo[NB][ST3] == approx(10 / 3)


@enforce_types
def test_mix_upper_and_lower_case():
    allocations = {C1: {NA: {ST1: 1.0}}}
    allocations2a = {C1: {NA: {ST1: 1.0}}}
    allocations2b = {C1: {"0xnfta_aDDr": {ST1: 1.0}}}
    allocations2c = {C1: {NA: {"0xsT1_aDdR": 1.0}}}

    nftvols = {C1: {OCN_ADDR: {NA: 10000.0}}}
    nftvols2a = {C1: {OCN_ADDR.upper(): {NA: 10000.0}}}
    nftvols2b = {C1: {OCN_ADDR: {"0xnfta_adDr": 10000.0}}}

    rates2 = {"oceaN": 0.5, "h2O": 1.6}

    vebals = {ST1: 10000.0, ST2: 10000.0, ST3: 10000.0}

    target_rewardsperlp = {C1: {ST1: 10.0}}
    target_rewardsinfo = {C1: {NA: {ST1: 10.0}}}
    rewards_avail_OCEAN = 10.0

    # sanity check
    cleancase.assertAllocations(allocations)
    cleancase.assertNftvols(nftvols)
    cleancase.assertRates(RATES)

    # the real tests
    rewardsperlp, rewardsinfo = _calcRewards(
        allocations2a, vebals, nftvols, rewards_avail_OCEAN
    )
    assert target_rewardsperlp == rewardsperlp
    assert target_rewardsinfo == rewardsinfo

    rewardsperlp, _ = _calcRewards(allocations2b, vebals, nftvols, rewards_avail_OCEAN)
    assert target_rewardsperlp == rewardsperlp
    assert target_rewardsinfo == rewardsinfo

    rewardsperlp, _ = _calcRewards(allocations2c, vebals, nftvols, rewards_avail_OCEAN)
    assert target_rewardsperlp == rewardsperlp
    assert target_rewardsinfo == rewardsinfo

    rewardsperlp, _ = _calcRewards(allocations, vebals, nftvols2a, rewards_avail_OCEAN)
    assert target_rewardsperlp == rewardsperlp
    assert target_rewardsinfo == rewardsinfo

    rewardsperlp, _ = _calcRewards(allocations, vebals, nftvols2b, rewards_avail_OCEAN)
    assert target_rewardsperlp == rewardsperlp
    assert target_rewardsinfo == rewardsinfo

    rewardsperlp, _ = _calcRewards(
        allocations, vebals, nftvols, rewards_avail_OCEAN, rates=rates2
    )
    assert target_rewardsperlp == rewardsperlp
    assert target_rewardsinfo == rewardsinfo


def test_calcrewards_math():
    ## update this test if the reward function is changed
    allocations = {C1: {NA: {ST1: 0.5, ST2: 1.0}, NB: {ST1: 0.5, ST3: 1.0}}}
    vebals = {ST1: 40000.0, ST2: 50000.0, ST3: 10000.0}
    nftvols = {C1: {OCN_ADDR: {NA: 32.0, NB: 8.0}}}
    rewards_avail_OCEAN = 100.0

    rewardsperlp, rewardsinfo = _calcRewardsC1(
        allocations, vebals, nftvols, rewards_avail_OCEAN
    )

    assert sum(rewardsperlp.values()) == pytest.approx(100.0, 0.01)

    assert rewardsperlp[ST1] == pytest.approx(32.25, 0.01)

    assert rewardsperlp[ST2] == pytest.approx(64.51, 0.01)
    assert rewardsperlp[ST3] == pytest.approx(3.22, 0.01)

    assert rewardsinfo[NA][ST1] == pytest.approx(25.86, 0.01)
    assert rewardsinfo[NA][ST2] == pytest.approx(64.51, 0.01)
    assert rewardsinfo[NB][ST1] == pytest.approx(6.45, 0.01)
    assert rewardsinfo[NB][ST3] == pytest.approx(3.22, 0.01)


@enforce_types
def test_bound_APY_one_nft():
    allocations = {C1: {NA: {ST1: 1.0}}}
    vebals = {ST1: 1.0}
    nftvols = {C1: {OCN_ADDR: {NA: 1.0}}}
    rewards_avail_OCEAN = 10000.0

    rewardsperlp, rewardsinfo = _calcRewardsC1(
        allocations, vebals, nftvols, rewards_avail_OCEAN
    )

    assert rewardsperlp == {ST1: 1.0 * TARGET_WPY}
    assert rewardsinfo == {NA: {ST1: 1.0 * TARGET_WPY}}


@enforce_types
def test_bound_APY_one_LP__high_stake__two_nfts():
    allocations = {C1: {NA: {ST1: 0.5}, NB: {ST1: 0.5}}}
    vebals = {ST1: 2e6}
    nftvols = {C1: {OCN_ADDR: {NA: 1.0, NB: 1.0}}}
    rewards_avail_OCEAN = 1000.0

    rewardsperlp, rewardsinfo = _calcRewardsC1(
        allocations, vebals, nftvols, rewards_avail_OCEAN
    )

    # ensure that total rewards given doesn't exceed rewards_avail
    assert rewardsperlp == {ST1: 1000.0}
    assert rewardsinfo == {NA: {ST1: 500.0}, NB: {ST1: 500.0}}


@enforce_types
def test_bound_APY_two_nfts__equal_low_stake__equal_low_DCV():
    allocations = {C1: {NA: {ST1: 1.0}, NB: {ST2: 1.0}}}
    vebals = {ST1: 5.0, ST2: 5.0}
    nftvols = {C1: {OCN_ADDR: {NA: 1.0, NB: 1.0}}}
    rewards_avail_OCEAN = 10000.0

    rewardsperlp, rewardsinfo = _calcRewardsC1(
        allocations, vebals, nftvols, rewards_avail_OCEAN
    )

    assert rewardsperlp == {ST1: 5.0 * TARGET_WPY, ST2: 5.0 * TARGET_WPY}
    assert rewardsinfo == {NA: {ST1: 5.0 * TARGET_WPY}, NB: {ST2: 5.0 * TARGET_WPY}}


@enforce_types
def test_bound_APY_two_nfts__both_low_stake__one_nft_dominates_stake():
    allocations = {C1: {NA: {ST1: 1.0}, NB: {ST2: 1.0}}}
    vebals = {ST1: 5.0, ST2: 20000.0}
    nftvols = {C1: {OCN_ADDR: {NA: 1.0, NB: 1.0}}}
    rewards_avail_OCEAN = 10000.0

    rewardsperlp, rewardsinfo = _calcRewardsC1(
        allocations, vebals, nftvols, rewards_avail_OCEAN
    )

    # ST1 and ST2 each have stake sufficiently low that TARGET_WPY bounds it.
    # But, ST2 staked more, so it earns more
    assert rewardsperlp == {ST1: 5.0 * TARGET_WPY, ST2: 20000.0 * TARGET_WPY}
    assert rewardsinfo == {
        NA: {ST1: 5.0 * TARGET_WPY},
        NB: {ST2: 20000 * TARGET_WPY},
    }


@enforce_types
def test_bound_APY_two_nfts__low_stake__one_nft_dominates_DCV():
    allocations = {C1: {NA: {ST1: 1.0}, NB: {ST2: 1.0}}}
    vebals = {ST1: 5.0, ST2: 5.0}
    nftvols = {C1: {OCN_ADDR: {NA: 1.0, NB: 10000.0}}}
    rewards_avail_OCEAN = 10000.0

    rewardsperlp, rewardsinfo = _calcRewardsC1(
        allocations, vebals, nftvols, rewards_avail_OCEAN
    )

    # ST1 and ST2 get same amount - they're both bounded because both have low stake
    # Critically, ST2 doesn't swamp ST1 just because ST2's stake * DCV is way higher
    assert rewardsperlp == {ST1: 5.0 * TARGET_WPY, ST2: 5.0 * TARGET_WPY}
    assert rewardsinfo == {NA: {ST1: 5.0 * TARGET_WPY}, NB: {ST2: 5.0 * TARGET_WPY}}


@enforce_types
def test_bound_APY_two_nfts__high_stake__one_nft_dominates_DCV():
    allocations = {C1: {NA: {ST1: 1.0}, NB: {ST2: 1.0}}}
    vebals = {ST1: 1e6, ST2: 1e6}
    nftvols = {C1: {OCN_ADDR: {NA: 1.0, NB: 9999.0}}}
    rewards_avail_OCEAN = 10000.0

    rewardsperlp, rewardsinfo = _calcRewardsC1(
        allocations, vebals, nftvols, rewards_avail_OCEAN
    )

    # ST2 reward swamps ST1 because ST2's stake * DCV is way higher; it's *not* bounded by low stake
    assert rewardsperlp == {ST1: 1.0, ST2: 9999.0}
    assert rewardsinfo == {NA: {ST1: 1.0}, NB: {ST2: 9999.0}}


@enforce_types
def test_divide_by_zero():
    allocations = {C1: {NA: {ST1: 1.0}, NB: {ST2: 1.0}}}
    vebals = {ST1: 10000.0, ST2: 10000.0}
    nftvols = {C1: {OCN_ADDR: {ST1: 0, ST2: 0}}}
    rewards_avail_OCEAN = 10000.0

    rewardsperlp, _ = _calcRewardsC1(allocations, vebals, nftvols, rewards_avail_OCEAN)

    # Should return empty dict because ST1 and ST2 have zero volume
    assert rewardsperlp == {}


@enforce_types
def test_alloc_vebal_mismatch():
    # ST2 has allocation but has no ve balance
    # ST1 has ve balance but no allocation
    # calcRewards should return an empty dict
    allocations = {C1: {NB: {ST2: 1.0}}}
    vebals = {
        ST1: 10000.0,
    }
    nftvols = {C1: {OCN_ADDR: {ST1: 1.0, ST2: 1.0}}}
    rewards_avail_OCEAN = 10000.0

    rewardsperlp, _ = _calcRewardsC1(allocations, vebals, nftvols, rewards_avail_OCEAN)

    assert rewardsperlp == {}


@enforce_types
def test_no_vebals():
    # ST2 has allocation, no ve balances
    # ST1 has ve balance but no allocation
    # calcRewards should return an empty dict
    allocations = {C1: {NB: {ST2: 1.0}}}
    vebals = {}
    nftvols = {C1: {OCN_ADDR: {ST1: 1.0, ST2: 1.0}}}
    rewards_avail_OCEAN = 100.0

    with pytest.raises(ValueError) as err:
        err = _calcRewardsC1(allocations, vebals, nftvols, rewards_avail_OCEAN)

    assert str(err.value) == "No veBalances provided"


@enforce_types
def test_no_allocations():
    # ST2 has allocation but has no ve balance
    # ST1 has ve balance but no allocation
    # calcRewards should return an empty dict
    allocations = {}
    vebals = {
        ST1: 10000.0,
    }
    nftvols = {C1: {OCN_ADDR: {ST1: 1.0, ST2: 1.0}}}
    rewards_avail_OCEAN = 100.0

    # should raise valueError "no allocations"
    with pytest.raises(ValueError) as err:
        err = _calcRewardsC1(allocations, vebals, nftvols, rewards_avail_OCEAN)

    assert str(err.value) == "No allocations provided"


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
