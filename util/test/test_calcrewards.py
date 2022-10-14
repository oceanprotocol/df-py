from enforce_typing import enforce_types
import pytest
from pytest import approx

from util import cleancase
from util.calcrewards import calcRewards, TARGET_WPY

# for shorter lines
RATES = {"OCEAN": 0.5, "H2O": 1.6, "UNAPP": 42.0, "PSDN": 0.01}
C1, C2 = 7, 137
PA, PB, PC = "0xnfta_addr", "0xnftb_addr", "0xnftc_addr"
LP1, LP2, LP3, LP4 = "0xlp1_addr", "0xlp2_addr", "0xlp3_addr", "0xlp4_addr"
OCN_SYMB, H2O_SYMB, UNAPP_SYMB = "OCEAN", "H2O", "UNAPP"
OCN_ADDR, H2O_ADDR, UNAPP_ADDR = "0xocean", "0xh2o", "0xunapp"
SYMBOLS = {
    C1: {OCN_ADDR: OCN_SYMB, H2O_ADDR: H2O_SYMB},
    C2: {"0xocean2": "OCEAN", "Oxh2o2": "H2O"},
}
APPROVED_TOKEN_ADDRS = {C1: [OCN_ADDR, H2O_ADDR], C2: ["0xocean2", "Oxh2o2"]}


@enforce_types
def test_simple():
    allocations = {C1: {PA: {LP1: 1.0}}}
    vebals = {LP1: 1000.0}
    nftvols = {C1: {OCN_ADDR: {PA: 1.0}}}

    rewards_avail_OCEAN = 10.0
    rewardsperlp, rewardsinfo = calcRewards(
        allocations,
        vebals,
        nftvols,
        SYMBOLS,
        RATES,
        rewards_avail_OCEAN,
        "OCEAN",
    )

    assert rewardsperlp == {C1: {LP1: 10.0}}
    assert rewardsinfo == {C1: {PA: {LP1: 10}}}


@enforce_types
def test_unapproved_addr():
    allocations = {C1: {PA: {LP1: 1.0 - 0.0002}, PC: {LP1: 0.0002}}}
    vebals = {LP1: 1000.0}
    nftvols = {C1: {OCN_ADDR: {PA: 1.0}, UNAPP_ADDR: {PC: 2.0}}}

    rewards_avail_OCEAN = 10.0
    rewardsperlp, rewardsinfo = calcRewards(
        allocations,
        vebals,
        nftvols,
        SYMBOLS,
        RATES,
        rewards_avail_OCEAN,
        "OCEAN",
    )

    assert rewardsperlp[C1][LP1] == approx(10.0, 0.01)
    assert rewardsinfo == {C1: {PA: {LP1: 10}}}


@enforce_types
def test_two_basetokens_OCEAN_and_H2O():
    allocations = {
        C1: {
            PA: {LP1: 0.5},
            PB: {LP1: 0.5},
        }
    }
    vebals = {LP1: 10000.0}
    nftvols = {
        C1: {OCN_ADDR: {PA: 40.0}, H2O_ADDR: {PB: 12.5}}  # vol in units of OCEAN
    }  # vol in units of H2O

    rates = {"OCEAN": 0.5, "H2O": 1.6}
    rewards_avail_OCEAN = 10.0
    rewardsperlp, rewardsinfo = calcRewards(
        allocations,
        vebals,
        nftvols,
        SYMBOLS,
        rates,
        rewards_avail_OCEAN,
        "OCEAN",
    )

    PA_RF_USD = 0.5 * 40.0 * 0.5
    PB_RF_USD = 0.5 * 12.5 * 1.6
    PA_amt = PA_RF_USD / (PA_RF_USD + PB_RF_USD) * 10.0
    PB_amt = PB_RF_USD / (PA_RF_USD + PB_RF_USD) * 10.0

    assert rewardsperlp == {C1: {LP1: 10.0}}
    assert rewardsinfo == {C1: {PA: {LP1: PA_amt}, PB: {LP1: PB_amt}}}


@enforce_types
def test_PSDN_rewards():
    allocations = {C1: {PA: {LP1: 0.5}, PB: {LP1: 0.5}}}
    vebals = {LP1: 10000.0}
    nftvols = {C1: {OCN_ADDR: {PA: 1.0 * 1.6 / 0.5}, H2O_ADDR: {PB: 1.0}}}

    rewards_avail_PSDN = 10.0
    rewardsperlp, rewardsinfo = calcRewards(
        allocations,
        vebals,
        nftvols,
        SYMBOLS,
        RATES,
        rewards_avail_PSDN,
        "PSDN",
    )

    # only give rewards to LPs of H2O nfts
    assert rewardsperlp[C1][LP1] == pytest.approx(10.0, 0.0000001)
    assert rewardsinfo[C1][PB][LP1] == pytest.approx(5.0, 0.0000001)
    assert rewardsinfo[C1][PA][LP1] == pytest.approx(5.0, 0.0000001)


@enforce_types
def test_two_chains():
    # first cut: symbols are the same
    allocations = {
        C1: {PA: {LP1: 0.5}},
        C2: {PB: {LP1: 0.5}},
    }
    vebals = {LP1: 100000.0}
    nftvols = {C1: {OCN_ADDR: {PA: 1.0}}, C2: {"0xocean2": {PB: 1.0}}}
    symbols = {
        C1: {OCN_ADDR: OCN_SYMB, H2O_ADDR: H2O_SYMB},
        C2: {"0xocean2": "OCEAN", "Oxh2o2": "H2O"},
    }
    rates = {"OCEAN": 0.5, "H2O": 1.6}

    target_rewardsperlp = {C1: {LP1: 10.0}, C2: {LP1: 10.0}}
    target_rewardsinfo = {C1: {PA: {LP1: 10.0}}, C2: {PB: {LP1: 10.0}}}

    rewards_avail_OCEAN = 20.0
    rewardsperlp, rewardsinfo = calcRewards(
        allocations,
        vebals,
        nftvols,
        symbols,
        rates,
        rewards_avail_OCEAN,
        "OCEAN",
    )
    assert rewardsperlp == target_rewardsperlp
    assert rewardsinfo == target_rewardsinfo

    # now, make it so that Ocean token in C2 is MOCEAN
    symbols[C2]["0xocean2"] = "MOCEAN"
    rewardsperlp, rewardsinfo = calcRewards(
        allocations,
        vebals,
        nftvols,
        symbols,
        rates,
        rewards_avail_OCEAN,
        "OCEAN",
    )
    assert rewardsperlp == {C1: {LP1: 20.0}}  # it completely ignores C2's MOCEAN ...
    assert rewardsinfo == {
        C1: {PA: {LP1: 20.0}}
    }  # ...but of course we don't want that...

    # ... so here's the intervention needed!
    rates["MOCEAN"] = rates["OCEAN"]

    rewardsperlp, rewardsinfo = calcRewards(
        allocations,
        vebals,
        nftvols,
        symbols,
        rates,
        rewards_avail_OCEAN,
        "OCEAN",
    )

    # now the rewards should line up as expected
    assert rewardsperlp == target_rewardsperlp
    assert rewardsinfo == target_rewardsinfo


@enforce_types
def test_two_lps_simple():
    allocations = {C1: {PA: {LP1: 1.0, LP2: 1.0}}}
    vebals = {LP1: 100000.0, LP2: 100000.0}
    nftvols = {C1: {OCN_ADDR: {PA: 1.0}}}

    rewards_avail_OCEAN = 10.0
    rewardsperlp, rewardsinfo = calcRewards(
        allocations,
        vebals,
        nftvols,
        SYMBOLS,
        RATES,
        rewards_avail_OCEAN,
        "OCEAN",
    )

    assert sum(rewardsperlp[C1].values()) == pytest.approx(10.0, 0.01)
    assert sum(rewardsinfo[C1][PA].values()) == pytest.approx(10.0, 0.01)
    assert rewardsperlp == {C1: {LP1: 5.0, LP2: 5.0}}
    assert rewardsinfo == {C1: {PA: {LP1: 5.0, LP2: 5.0}}}


@enforce_types
def test_two_lps_one_with_negligible_stake():
    allocations = {C1: {PA: {LP1: 1.0, LP2: 1e-14}}}
    vebals = {LP1: 10000.0, LP2: 10000.0}
    nftvols = {C1: {OCN_ADDR: {PA: 1.0}}}
    rewards_avail_OCEAN = 10.0
    rewardsperlp, rewardsinfo = calcRewards(
        allocations,
        vebals,
        nftvols,
        SYMBOLS,
        RATES,
        rewards_avail_OCEAN,
        "OCEAN",
    )
    assert sum(rewardsperlp[C1].values()) == pytest.approx(10.0, 0.01)
    assert sum(rewardsinfo[C1][PA].values()) == pytest.approx(10.0, 0.01)
    assert rewardsperlp == {C1: {LP1: 10.0}}  # no entry for LP2
    assert rewardsinfo == {C1: {PA: {LP1: 10.0}}}  # no entry for LP2


@enforce_types
def test_two_nfts_one_with_volume():
    allocations = {
        C1: {
            PA: {LP1: 1.0, LP2: 1.0},
            PB: {LP3: 1.0},
        }
    }
    vebals = {LP1: 10000.0, LP2: 10000.0, LP3: 10000.0}
    nftvols = {C1: {OCN_ADDR: {PA: 1.0}}}  # P1 has volume, but not P2
    rewards_avail_OCEAN = 10.0
    rewardsperlp, rewardsinfo = calcRewards(
        allocations,
        vebals,
        nftvols,
        SYMBOLS,
        RATES,
        rewards_avail_OCEAN,
        "OCEAN",
    )
    assert sum(rewardsperlp[C1].values()) == pytest.approx(10.0, 0.01)
    assert min(rewardsperlp[C1].values()) > 0, "shouldn't have entries with 0 rewards"
    assert rewardsperlp == {C1: {LP1: 5.0, LP2: 5.0}}

    assert sum(rewardsinfo[C1][PA].values()) == pytest.approx(10.0, 0.01)
    assert (
        min(rewardsinfo[C1][PA].values()) > 0
    ), "shouldn't have entries with 0 rewards"
    assert rewardsinfo == {C1: {PA: {LP1: 5.0, LP2: 5.0}}}


@enforce_types
def test_two_nfts_both_with_volume():
    allocations = {
        C1: {
            PA: {LP1: 0.5, LP2: 1.0},
            PB: {LP1: 0.5, LP3: 1.0},
        }
    }
    vebals = {LP1: 10000.0, LP2: 10000.0, LP3: 10000.0}
    nftvols = {C1: {OCN_ADDR: {PA: 1.0, PB: 1.0}}}  # P1 & P2 both have volume
    rewards_avail_OCEAN = 10.0
    rewardsperlp, rewardsinfo = calcRewards(
        allocations,
        vebals,
        nftvols,
        SYMBOLS,
        RATES,
        rewards_avail_OCEAN,
        "OCEAN",
    )
    assert sum(rewardsperlp[C1].values()) == pytest.approx(10.0, 0.01)
    assert rewardsperlp[C1][LP1] == rewardsperlp[C1][LP2]
    assert rewardsperlp[C1][LP1] == rewardsperlp[C1][LP3]
    assert rewardsperlp[C1][LP2] == rewardsperlp[C1][LP3]

    assert sum(rewardsinfo[C1][PA].values()) == pytest.approx(5.0, 0.01)
    assert sum(rewardsinfo[C1][PB].values()) == pytest.approx(5.0, 0.01)
    assert rewardsinfo[C1][PA][LP1] == approx(10 / 3 / 2)
    assert rewardsinfo[C1][PB][LP1] == approx(10 / 3 / 2)
    assert rewardsinfo[C1][PA][LP2] == approx(10 / 3)
    assert rewardsinfo[C1][PB][LP3] == approx(10 / 3)


@enforce_types
def test_mix_upper_and_lower_case():
    # PA, PB, PC = "0xnfta_addr", "0xnftb_addr", "0xnftc_addr"
    # LP1, LP2, LP3, LP4 = "0xlp1_addr", "0xlp2_addr", "0xlp3_addr", "lp4_addr"
    # OCN_ADDR, H2O = "0xocean", "0xh2o"

    allocations = {C1: {PA: {LP1: 1.0}}}
    allocations2a = {C1: {PA: {LP1: 1.0}}}
    allocations2b = {C1: {"0xnfta_aDDr": {LP1: 1.0}}}
    allocations2c = {C1: {PA: {"0xlP1_aDdR": 1.0}}}

    nftvols = {C1: {OCN_ADDR: {PA: 10000.0}}}
    nftvols2a = {C1: {OCN_ADDR.upper(): {PA: 10000.0}}}
    nftvols2b = {C1: {OCN_ADDR: {"0xnfta_adDr": 10000.0}}}

    rates = {"OCEAN": 0.5, "H2O": 1.6}
    rates2 = {"oceaN": 0.5, "h2O": 1.6}

    vebals = {LP1: 10000.0, LP2: 10000.0, LP3: 10000.0}

    target_rewardsperlp = {C1: {LP1: 10.0}}
    target_rewardsinfo = {C1: {PA: {LP1: 10.0}}}
    rewards_avail_OCEAN = 10.0

    # sanity check
    cleancase.assertAllocations(allocations)
    cleancase.assertNFTvols(nftvols)
    cleancase.assertRates(rates)

    # the real tests
    rewardsperlp, rewardsinfo = calcRewards(
        allocations2a,
        vebals,
        nftvols,
        SYMBOLS,
        rates,
        rewards_avail_OCEAN,
        "OCEAN",
    )
    assert target_rewardsperlp == rewardsperlp
    assert target_rewardsinfo == rewardsinfo

    rewardsperlp, _ = calcRewards(
        allocations2b,
        vebals,
        nftvols,
        SYMBOLS,
        rates,
        rewards_avail_OCEAN,
        "OCEAN",
    )
    assert target_rewardsperlp == rewardsperlp
    assert target_rewardsinfo == rewardsinfo

    rewardsperlp, _ = calcRewards(
        allocations2c,
        vebals,
        nftvols,
        SYMBOLS,
        rates,
        rewards_avail_OCEAN,
        "OCEAN",
    )
    assert target_rewardsperlp == rewardsperlp
    assert target_rewardsinfo == rewardsinfo

    rewardsperlp, _ = calcRewards(
        allocations,
        vebals,
        nftvols2a,
        SYMBOLS,
        rates,
        rewards_avail_OCEAN,
        "OCEAN",
    )
    assert target_rewardsperlp == rewardsperlp
    assert target_rewardsinfo == rewardsinfo

    rewardsperlp, _ = calcRewards(
        allocations,
        vebals,
        nftvols2b,
        SYMBOLS,
        rates,
        rewards_avail_OCEAN,
        "OCEAN",
    )
    assert target_rewardsperlp == rewardsperlp
    assert target_rewardsinfo == rewardsinfo

    rewardsperlp, _ = calcRewards(
        allocations,
        vebals,
        nftvols,
        SYMBOLS,
        rates2,
        rewards_avail_OCEAN,
        "OCEAN",
    )
    assert target_rewardsperlp == rewardsperlp
    assert target_rewardsinfo == rewardsinfo


def test_calcrewards_math():
    ## update this test if the reward function is changes

    allocations = {C1: {PA: {LP1: 0.5, LP2: 1.0}, PB: {LP1: 0.5, LP3: 1.0}}}
    vebals = {LP1: 40000.0, LP2: 50000.0, LP3: 10000.0}
    nftvols = {C1: {OCN_ADDR: {PA: 32.0, PB: 8.0}}}
    rewards_avail_OCEAN = 100.0
    rewardsperlp, rewardsinfo = calcRewards(
        allocations,
        vebals,
        nftvols,
        SYMBOLS,
        RATES,
        rewards_avail_OCEAN,
        "OCEAN",
    )

    assert sum(rewardsperlp[C1].values()) == pytest.approx(100.0, 0.01)

    assert rewardsperlp[C1][LP1] == pytest.approx(32.25, 0.01)

    assert rewardsperlp[C1][LP2] == pytest.approx(64.51, 0.01)
    assert rewardsperlp[C1][LP3] == pytest.approx(3.22, 0.01)

    assert rewardsinfo[C1][PA][LP1] == pytest.approx(25.86, 0.01)
    assert rewardsinfo[C1][PA][LP2] == pytest.approx(64.51, 0.01)
    assert rewardsinfo[C1][PB][LP1] == pytest.approx(6.45, 0.01)
    assert rewardsinfo[C1][PB][LP3] == pytest.approx(3.22, 0.01)


@enforce_types
def test_bound_APY_one_nft():
    allocations = {C1: {PA: {LP1: 1.0}}}
    vebals = {LP1: 1.0}
    nftvols = {C1: {OCN_ADDR: {PA: 1.0}}}

    rewards_avail_OCEAN = 10000.0
    rewardsperlp, rewardsinfo = calcRewards(
        allocations,
        vebals,
        nftvols,
        SYMBOLS,
        RATES,
        rewards_avail_OCEAN,
        "OCEAN",
    )
    assert rewardsperlp[C1] == {LP1: 1.0 * TARGET_WPY}
    assert rewardsinfo[C1] == {PA: {LP1: 1.0 * TARGET_WPY}}


@enforce_types
def test_bound_APY_one_LP__high_stake__two_nfts():
    allocations = {C1: {PA: {LP1: 0.5}, PB: {LP1: 0.5}}}
    vebals = {LP1: 2e6}
    nftvols = {C1: {OCN_ADDR: {PA: 1.0, PB: 1.0}}}

    rewards_avail_OCEAN = 1000.0
    rewardsperlp, rewardsinfo = calcRewards(
        allocations,
        vebals,
        nftvols,
        SYMBOLS,
        RATES,
        rewards_avail_OCEAN,
        "OCEAN",
    )

    # ensure that total rewards given doesn't exceed rewards_avail
    assert rewardsperlp[C1] == {LP1: 1000.0}
    assert rewardsinfo[C1] == {PA: {LP1: 500.0}, PB: {LP1: 500.0}}


@enforce_types
def test_bound_APY_two_nfts__equal_low_stake__equal_low_DCV():
    allocations = {C1: {PA: {LP1: 1.0}, PB: {LP2: 1.0}}}
    vebals = {LP1: 5.0, LP2: 5.0}
    nftvols = {C1: {OCN_ADDR: {PA: 1.0, PB: 1.0}}}

    rewards_avail_OCEAN = 10000.0
    rewardsperlp, rewardsinfo = calcRewards(
        allocations,
        vebals,
        nftvols,
        SYMBOLS,
        RATES,
        rewards_avail_OCEAN,
        "OCEAN",
    )

    assert rewardsperlp[C1] == {LP1: 5.0 * TARGET_WPY, LP2: 5.0 * TARGET_WPY}
    assert rewardsinfo[C1] == {PA: {LP1: 5.0 * TARGET_WPY}, PB: {LP2: 5.0 * TARGET_WPY}}


@enforce_types
def test_bound_APY_two_nfts__both_low_stake__one_nft_dominates_stake():
    allocations = {C1: {PA: {LP1: 1.0}, PB: {LP2: 1.0}}}
    vebals = {LP1: 5.0, LP2: 20000.0}
    nftvols = {C1: {OCN_ADDR: {PA: 1.0, PB: 1.0}}}

    rewards_avail_OCEAN = 10000.0
    rewardsperlp, rewardsinfo = calcRewards(
        allocations,
        vebals,
        nftvols,
        SYMBOLS,
        RATES,
        rewards_avail_OCEAN,
        "OCEAN",
    )

    # LP1 and LP2 each have stake sufficiently low that TARGET_WPY bounds it.
    # But, LP2 staked more, so it earns more
    assert rewardsperlp[C1] == {LP1: 5.0 * TARGET_WPY, LP2: 20000.0 * TARGET_WPY}
    assert rewardsinfo[C1] == {
        PA: {LP1: 5.0 * TARGET_WPY},
        PB: {LP2: 20000 * TARGET_WPY},
    }


@enforce_types
def test_bound_APY_two_nfts__low_stake__one_nft_dominates_DCV():
    allocations = {C1: {PA: {LP1: 1.0}, PB: {LP2: 1.0}}}
    vebals = {LP1: 5.0, LP2: 5.0}
    nftvols = {C1: {OCN_ADDR: {PA: 1.0, PB: 10000.0}}}

    rewards_avail_OCEAN = 10000.0
    rewardsperlp, rewardsinfo = calcRewards(
        allocations,
        vebals,
        nftvols,
        SYMBOLS,
        RATES,
        rewards_avail_OCEAN,
        "OCEAN",
    )

    # LP1 and LP2 get same amount - they're both bounded because both have low stake
    # Critically, LP2 doesn't swamp LP1 just because LP2's stake * DCV is way higher
    assert rewardsperlp[C1] == {LP1: 5.0 * TARGET_WPY, LP2: 5.0 * TARGET_WPY}
    assert rewardsinfo[C1] == {PA: {LP1: 5.0 * TARGET_WPY}, PB: {LP2: 5.0 * TARGET_WPY}}


@enforce_types
def test_bound_APY_two_nfts__high_stake__one_nft_dominates_DCV():
    allocations = {C1: {PA: {LP1: 1.0}, PB: {LP2: 1.0}}}
    vebals = {LP1: 1e6, LP2: 1e6}
    nftvols = {C1: {OCN_ADDR: {PA: 1.0, PB: 9999.0}}}

    rewards_avail_OCEAN = 10000.0
    rewardsperlp, rewardsinfo = calcRewards(
        allocations,
        vebals,
        nftvols,
        SYMBOLS,
        RATES,
        rewards_avail_OCEAN,
        "OCEAN",
    )

    # LP2 reward swamps LP1 because LP2's stake * DCV is way higher; it's *not* bounded by low stake
    assert rewardsperlp[C1] == {LP1: 1.0, LP2: 9999.0}
    assert rewardsinfo[C1] == {PA: {LP1: 1.0}, PB: {LP2: 9999.0}}


@enforce_types
def test_divide_by_zero():
    allocations = {C1: {PA: {LP1: 1.0}, PB: {LP2: 1.0}}}
    vebals = {LP1: 10000.0, LP2: 10000.0}
    nftvols = {C1: {OCN_ADDR: {LP1: 0, LP2: 0}}}

    rewards_avail_OCEAN = 10000.0
    rewardsperlp, _ = calcRewards(
        allocations,
        vebals,
        nftvols,
        SYMBOLS,
        RATES,
        rewards_avail_OCEAN,
        "OCEAN",
    )

    # Should return empty dict because LP1 and LP2 have zero volume
    assert rewardsperlp == {}


@enforce_types
def test_alloc_vebal_mismatch():
    # LP2 has allocation but has no ve balance
    # LP1 has ve balance but no allocation
    # calcRewards should return an empty dict
    allocations = {C1: {PB: {LP2: 1.0}}}
    vebals = {
        LP1: 10000.0,
    }
    nftvols = {C1: {OCN_ADDR: {LP1: 1.0, LP2: 1.0}}}

    rewards_avail_OCEAN = 10000.0
    rewardsperlp, _ = calcRewards(
        allocations,
        vebals,
        nftvols,
        SYMBOLS,
        RATES,
        rewards_avail_OCEAN,
        "OCEAN",
    )

    assert rewardsperlp == {}


@enforce_types
def test_no_vebals():
    # LP2 has allocation, no ve balances
    # LP1 has ve balance but no allocation
    # calcRewards should return an empty dict
    allocations = {C1: {PB: {LP2: 1.0}}}
    vebals = {}
    nftvols = {C1: {OCN_ADDR: {LP1: 1.0, LP2: 1.0}}}

    with pytest.raises(ValueError) as err:
        calcRewards(
            allocations,
            vebals,
            nftvols,
            SYMBOLS,
            RATES,
            10000.0,
            "OCEAN",
        )

    assert str(err.value) == "No veBalances provided"


@enforce_types
def test_no_allocations():
    # LP2 has allocation but has no ve balance
    # LP1 has ve balance but no allocation
    # calcRewards should return an empty dict
    allocations = {}
    vebals = {
        LP1: 10000.0,
    }
    nftvols = {C1: {OCN_ADDR: {LP1: 1.0, LP2: 1.0}}}

    # should raise valueError "no allocations"
    with pytest.raises(ValueError) as err:
        err = calcRewards(
            allocations,
            vebals,
            nftvols,
            SYMBOLS,
            RATES,
            10000.0,
            "OCEAN",
        )

    assert str(err.value) == "No allocations provided"
