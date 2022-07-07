from enforce_typing import enforce_types
import pytest

from util import cleancase, tok
from util.calcrewards import calcRewards, TARGET_WPY

# for shorter lines
RATES = {"OCEAN": 0.5, "H2O": 1.6, "UNAPP": 42.0}
C1, C2 = 7, 137
PA, PB, PC = "0xpoola_addr", "0xpoolb_addr", "0xpoolc_addr"
LP1, LP2, LP3, LP4 = "0xlp1_addr", "0xlp2_addr", "0xlp3_addr", "0xlp4_addr"
OCN_SYMB, H2O_SYMB, UNAPP_SYMB = "OCEAN", "H2O", "UNAPP"
OCN_ADDR, H2O_ADDR, UNAPP_ADDR = "0xocean", "0xh2o", "0xunapp"

APPROVED_TOKENS = tok.TokSet(
    [
        (C1, OCN_ADDR, OCN_SYMB),
        (C1, H2O_ADDR, H2O_SYMB),
        (C2, OCN_ADDR, OCN_SYMB),
        (C2, H2O_ADDR, H2O_SYMB),
    ]
)
TOK_SET = APPROVED_TOKENS
REWARDS_SYMBOL = OCN_SYMB


@enforce_types
def test_simple():
    stakes = {C1: {OCN_ADDR: {PA: {LP1: 10000.0}}}}
    poolvols = {C1: {OCN_ADDR: {PA: 1.0}}}
    
    rewards_avail_TOKEN = 10.0
    rewardsperlp, rewardsinfo = calcRewards(
        stakes, poolvols, APPROVED_TOKENS, RATES, rewards_avail_TOKEN, REWARDS_SYMBOL
    )
    
    assert rewardsperlp == {C1: {LP1: 10.0}} 
    assert rewardsinfo == {C1: {PA: {LP1: 10}}} 


@enforce_types
def test_unapproved_addr():
    stakes = {C1: {OCN_ADDR: {PA: {LP1: 10000.0}}, UNAPP_ADDR: {PC: {LP1: 20.0}}}}
    poolvols = {C1: {OCN_ADDR: {PA: 1.0}, UNAPP_ADDR: {PC: 2.0}}}
    
    rewards_avail_TOKEN = 10.0
    rewardsperlp, rewardsinfo = calcRewards(
        stakes, poolvols, APPROVED_TOKENS, RATES, rewards_avail_TOKEN, REWARDS_SYMBOL
    )

    assert rewardsperlp == {C1: {LP1: 10.0}} #ensure UNAPPR_ADDR doesn't show up
    assert rewardsinfo == {C1: {PA: {LP1: 10}}}


@enforce_types
def test_two_chains():
    stakes = {
        C1: {OCN_ADDR: {PA: {LP1: 10000.0}}},
        C2: {OCN_ADDR: {PB: {LP1: 10000.0}}},
    }
    poolvols = {C1: {OCN_ADDR: {PA: 1.0}}, C2: {OCN_ADDR: {PB: 1.0}}}
    
    rewards_avail_TOKEN = 20.0
    rewardsperlp, rewardsinfo = calcRewards(
        stakes, poolvols, APPROVED_TOKENS, RATES, rewards_avail_TOKEN, REWARDS_SYMBOL
    )

    assert rewardsperlp == {C1: {LP1: 10.0}, C2: {LP1: 10.0}}
    assert rewardsinfo == {C1: {PA: {LP1: 10.0}}, C2: {PB: {LP1: 10.0}}}


@enforce_types
def test_two_lps_simple():
    stakes = {C1: {OCN_ADDR: {PA: {LP1: 10000.0, LP2: 10000.0}}}}
    poolvols = {C1: {OCN_ADDR: {PA: 1.0}}}
    
    rewards_avail_TOKEN = 10.0
    rewardsperlp, rewardsinfo = calcRewards(
        stakes, poolvols, APPROVED_TOKENS, RATES, rewards_avail_TOKEN, REWARDS_SYMBOL
    )
    
    assert sum(rewardsperlp[C1].values()) == pytest.approx(10.0, 0.01)
    assert sum(rewardsinfo[C1][PA].values()) == pytest.approx(10.0, 0.01)
    assert rewardsperlp == {C1: {LP1: 5.0, LP2: 5.0}}
    assert rewardsinfo == {C1: {PA: {LP1: 5.0, LP2: 5.0}}}


@enforce_types
def test_two_lps_one_with_negligible_stake():
    stakes = {C1: {OCN_ADDR: {PA: {LP1: 10000.0, LP2: 1e-10}}}}
    poolvols = {C1: {OCN_ADDR: {PA: 1.0}}}
    rewards_avail_TOKEN = 10.0
    rewardsperlp, rewardsinfo = calcRewards(
        stakes, poolvols, APPROVED_TOKENS, RATES, rewards_avail_TOKEN, REWARDS_SYMBOL
    )
    assert sum(rewardsperlp[C1].values()) == pytest.approx(10.0, 0.01)
    assert sum(rewardsinfo[C1][PA].values()) == pytest.approx(10.0, 0.01)
    assert rewardsperlp == {C1: {LP1: 10.0}} # no entry for LP2
    assert rewardsinfo == {C1: {PA: {LP1: 10.0}}} # no entry for LP2


@enforce_types
def test_two_pools_one_with_volume():
    stakes = {
        C1: {
            OCN_ADDR: {
                PA: {LP1: 10000.0, LP2: 10000.0},
                PB: {LP1: 10000.0, LP3: 10000.0},
            }
        }
    }
    poolvols = {C1: {OCN_ADDR: {PA: 1.0}}}  # P1 has volume, but not P2
    rewards_avail_TOKEN = 10.0
    rewardsperlp, rewardsinfo = calcRewards(
        stakes, poolvols, APPROVED_TOKENS, RATES, rewards_avail_TOKEN, REWARDS_SYMBOL
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
def test_two_pools_both_with_volume():
    stakes = {
        C1: {
            OCN_ADDR: {
                PA: {LP1: 10000.0, LP2: 10000.0},
                PB: {LP1: 10000.0, LP3: 10000.0},
            }
        }
    }
    poolvols = {C1: {OCN_ADDR: {PA: 1.0, PB: 1.0}}}  # P1 & P2 both have volume
    rewards_avail_TOKEN = 10.0
    rewardsperlp, rewardsinfo = calcRewards(
        stakes, poolvols, APPROVED_TOKENS, RATES, rewards_avail_TOKEN, REWARDS_SYMBOL
    )
    assert sum(rewardsperlp[C1].values()) == pytest.approx(10.0, 0.01)
    assert rewardsperlp == {C1: {LP1: 5.0, LP2: 2.5, LP3: 2.5}}

    assert sum(rewardsinfo[C1][PA].values()) == pytest.approx(5.0, 0.01)
    assert sum(rewardsinfo[C1][PB].values()) == pytest.approx(5.0, 0.01)
    assert rewardsinfo == {C1: {PA: {LP1: 2.5, LP2: 2.5}, PB: {LP1: 2.5, LP3: 2.5}}}


@enforce_types
def test_mix_upper_and_lower_case():
    # PA, PB, PC = "0xpoola_addr", "0xpoolb_addr", "0xpoolc_addr"
    # LP1, LP2, LP3, LP4 = "0xlp1_addr", "0xlp2_addr", "0xlp3_addr", "lp4_addr"
    # OCN_ADDR, H2O = "0xocean", "0xh2o"

    stakes = {C1: {OCN_ADDR: {PA: {LP1: 10000.0}}}}
    stakes2a = {C1: {OCN_ADDR.upper(): {PA: {LP1: 10000.0}}}}
    stakes2b = {C1: {OCN_ADDR: {"0xpOoLa_aDDr": {LP1: 10000.0}}}}
    stakes2c = {C1: {OCN_ADDR: {PA: {"0xlP1_aDdR": 10000.0}}}}

    poolvols = {C1: {OCN_ADDR: {PA: 10000.0}}}
    poolvols2a = {C1: {OCN_ADDR.upper(): {PA: 10000.0}}}
    poolvols2b = {C1: {OCN_ADDR: {"0xpOola_adDr": 10000.0}}}

    rates = {"OCEAN": 0.5, "H2O": 1.6}
    rates2 = {"oceaN": 0.5, "h2O": 1.6}

    target_rewardsperlp = {C1: {LP1: 10.0}}
    target_rewardsinfo = {C1: {PA: {LP1: 10.0}}}
    rewards_avail_TOKEN = 10.0

    # sanity check
    cleancase.assertStakes(stakes)
    cleancase.assertPoolvols(poolvols)
    cleancase.assertRates(rates)

    # the real tests
    rewardsperlp, rewardsinfo = calcRewards(
        stakes2a, poolvols, APPROVED_TOKENS, rates, rewards_avail_TOKEN, REWARDS_SYMBOL
    )
    assert target_rewardsperlp == rewardsperlp
    assert target_rewardsinfo == rewardsinfo

    rewardsperlp, _ = calcRewards(
        stakes2b, poolvols, APPROVED_TOKENS, rates, rewards_avail_TOKEN, REWARDS_SYMBOL
    )
    assert target_rewardsperlp == rewardsperlp
    assert target_rewardsinfo == rewardsinfo

    rewardsperlp, _ = calcRewards(
        stakes2c, poolvols, APPROVED_TOKENS, rates, rewards_avail_TOKEN, REWARDS_SYMBOL
    )
    assert target_rewardsperlp == rewardsperlp
    assert target_rewardsinfo == rewardsinfo

    rewardsperlp, _ = calcRewards(
        stakes, poolvols2a, APPROVED_TOKENS, rates, rewards_avail_TOKEN, REWARDS_SYMBOL
    )
    assert target_rewardsperlp == rewardsperlp
    assert target_rewardsinfo == rewardsinfo

    rewardsperlp, _ = calcRewards(
        stakes, poolvols2b, APPROVED_TOKENS, rates, rewards_avail_TOKEN, REWARDS_SYMBOL
    )
    assert target_rewardsperlp == rewardsperlp
    assert target_rewardsinfo == rewardsinfo

    rewardsperlp, _ = calcRewards(
        stakes, poolvols, APPROVED_TOKENS, rates2, rewards_avail_TOKEN, REWARDS_SYMBOL
    )
    assert target_rewardsperlp == rewardsperlp
    assert target_rewardsinfo == rewardsinfo


def test_calcrewards_math():
    ## update this test when the reward function is changed

    stakes = {
        C1: {OCN_ADDR: {PA: {LP1: 20000, LP2: 50000}, PB: {LP1: 20000, LP3: 10000}}}
    }
    poolvols = {C1: {OCN_ADDR: {PA: 32.0, PB: 8.0}}}
    rewards_avail_TOKEN = 100.0
    rewardsperlp, rewardsinfo = calcRewards(
        stakes, poolvols, APPROVED_TOKENS, RATES, rewards_avail_TOKEN, REWARDS_SYMBOL
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
def test_bound_APY_one_pool():
    stakes = {C1: {OCN_ADDR: {PA: {LP1: 5.0}}}}
    poolvols = {C1: {OCN_ADDR: {PA: 1.0}}}

    rewards_avail_TOKEN = 10000.0
    rewardsperlp, rewardsinfo = calcRewards(
        stakes, poolvols, APPROVED_TOKENS, RATES, rewards_avail_TOKEN, REWARDS_SYMBOL
    )

    assert rewardsperlp == {C1: {LP1: 5.0 * TARGET_WPY}}
    assert rewardsinfo == {C1: {PA: {LP1: 5.0 * TARGET_WPY}}}


@enforce_types
def test_bound_APY_two_pools__equal_low_stake__equal_low_DCV():
    stakes = {C1: {OCN_ADDR: {PA: {LP1: 5.0}, PB: {LP2: 5.0}}}}
    poolvols = {C1: {OCN_ADDR: {PA: 1.0, PB: 1.0}}}

    rewards_avail_TOKEN = 10000.0
    rewardsperlp, rewardsinfo = calcRewards(
        stakes, poolvols, APPROVED_TOKENS, RATES, rewards_avail_TOKEN, REWARDS_SYMBOL
    )

    assert rewardsperlp == {C1: {LP1: 5.0 * TARGET_WPY, LP2: 5.0 * TARGET_WPY}}
    assert rewardsinfo == {C1: {PA: {LP1: 5.0 * TARGET_WPY}, PB: {LP2: 5.0 * TARGET_WPY}}}


@enforce_types
def test_bound_APY_two_pools__both_low_stake__one_pool_dominates_stake():
    stakes = {C1: {OCN_ADDR: {PA: {LP1: 5.0}, PB: {LP2: 20000.0}}}}
    poolvols = {C1: {OCN_ADDR: {PA: 1.0, PB: 1.0}}}

    rewards_avail_TOKEN = 10000.0
    rewardsperlp, rewardsinfo = calcRewards(
        stakes, poolvols, APPROVED_TOKENS, RATES, rewards_avail_TOKEN, REWARDS_SYMBOL
    )

    #LP1 and LP2 each have stake sufficiently low that TARGET_WPY bounds it. But, LP2 staked more
    # so it earns more
    assert rewardsperlp == {C1: {LP1: 5.0*TARGET_WPY, LP2: 20000.0*TARGET_WPY}}
    assert rewardsinfo == {C1: {PA: {LP1: 5.0*TARGET_WPY}, PB: {LP2: LP2: 10000 - 5.0*TARGET_WPY}}}


@enforce_types
def test_bound_APY_two_pools__low_stake__one_pool_dominates_DCV():
    stakes = {C1: {OCN_ADDR: {PA: {LP1: 5.0}, PB: {LP2: 5.0}}}}
    poolvols = {C1: {OCN_ADDR: {PA: 1.0, PB: 10000.0}}}

    rewards_avail_TOKEN = 10000.0
    rewardsperlp, rewardsinfo = calcRewards(
        stakes, poolvols, APPROVED_TOKENS, RATES, rewards_avail_TOKEN, REWARDS_SYMBOL
    )

    #LP1 and LP2 get same amount - they're both bounded because both have low stake
    #Critically, LP2 doesn't swamp LP1 just because LP2's stake * DCV is way higher
    assert rewardsperlp == {C1: {LP1: 5.0 * TARGET_WPY, LP2: 5.0 * TARGET_WPY}}
    assert rewardsinfo == {C1: {PA: {LP1: 5.0 * TARGET_WPY}, PB: {LP2: 5.0 * TARGET_WPY}}}


@enforce_types
def test_bound_APY_two_pools__high_stake__one_pool_dominates_DCV():
    stakes = {C1: {OCN_ADDR: {PA: {LP1: 1e6}, PB: {LP2: 1e6}}}}
    poolvols = {C1: {OCN_ADDR: {PA: 1.0, PB: 9999.0}}}

    rewards_avail_TOKEN = 10000.0
    rewardsperlp, rewardsinfo = calcRewards(
        stakes, poolvols, APPROVED_TOKENS, RATES, rewards_avail_TOKEN, REWARDS_SYMBOL
    )
    
    #LP2 reward swamps LP1 because LP2's stake * DCV is way higher; it's *not* bounded by low stake
    assert rewardsperlp == {C1: {LP1: 1.0, LP2: 9999.0}}
    assert rewardsinfo == {C1: {PA: {LP1: 1.0}, PB: {LP2: 9999.0}}}

