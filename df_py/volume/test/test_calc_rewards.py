# pylint: disable=too-many-lines
from unittest.mock import MagicMock, patch

import numpy as np
import pytest
from enforce_typing import enforce_types
from pytest import approx

from df_py.util.constants import PREDICTOOR_OCEAN_BUDGET, ZERO_ADDRESS
from df_py.volume import csvs
from df_py.volume.calc_rewards import calc_volume_rewards_from_csvs
from df_py.volume.reward_calculator import TARGET_WPY, RewardCalculator
from df_py.volume.test.constants import *  # pylint: disable=wildcard-import
from df_py.volume.test.helperfuncs import *  # pylint: disable=wildcard-import


class MockRewardCalculator(RewardCalculator):
    def __init__(self):
        super().__init__({}, {}, {}, {}, {}, {}, DF_WEEK, False, False, False)

    def set_mock_attribute(self, attr_name, attr_value):
        self._freeze_attributes = False
        setattr(self, attr_name, attr_value)
        self._freeze_attributes = True

    def set_V_USD(self, V_USD):
        self.set_mock_attribute("V_USD", V_USD)


@enforce_types
def test_freeze_attributes():
    rc = MockRewardCalculator()
    rc._freeze_attributes = True

    with pytest.raises(AttributeError):
        rc.new_attr = 1  # pylint: disable=attribute-defined-outside-init

    rc._freeze_attributes = False
    rc.new_attr = 1  # pylint: disable=attribute-defined-outside-init


@patch(QUERY_PATH, MagicMock(return_value={}))
@enforce_types
def test_simple():
    stakes = {C1: {NA: {LP1: 1000.0}}}
    locked_amts = {C1: {NA: {LP1: 1000.0}}}
    nftvols = {C1: {OCN_ADDR: {NA: 1.0}}}
    OCEAN_avail = 10.0

    rewards_per_lp, rewards_info = calc_rewards_(
        stakes, locked_amts, nftvols, OCEAN_avail
    )
    assert rewards_per_lp == {C1: {LP1: 10.0}}
    assert rewards_info == {C1: {NA: {LP1: 10}}}

    # test helper - just C1
    rewards_per_lp, rewards_info = calc_rewards_C1(stakes, nftvols, OCEAN_avail)
    assert rewards_per_lp == {LP1: 10.0}
    assert rewards_info == {NA: {LP1: 10}}


@patch(QUERY_PATH, MagicMock(return_value={}))
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
    rewards_per_lp, rewards_info = calc_rewards_C1(stakes, nftvols, OCEAN_avail)

    NA_RF_USD = 0.5 * 40.0 * 0.5
    NB_RF_USD = 0.5 * 12.5 * 1.6
    NA_amt = NA_RF_USD / (NA_RF_USD + NB_RF_USD) * 10.0
    NB_amt = NB_RF_USD / (NA_RF_USD + NB_RF_USD) * 10.0

    assert rewards_per_lp == {LP1: 10.0}
    assert rewards_info == {NA: {LP1: NA_amt}, NB: {LP1: NB_amt}}


@patch(QUERY_PATH, MagicMock(return_value={}))
@enforce_types
def test_two_chains():
    # first cut: symbols are the same
    stakes = {
        C1: {NA: {LP1: 50000.0}},
        C2: {NB: {LP1: 50000.0}},
    }
    locked_amts = {
        C1: {NA: {LP1: 50000.0}},
        C2: {NB: {LP1: 50000.0}},
    }
    nftvols = {C1: {OCN_ADDR: {NA: 1.0}}, C2: {OCN_ADDR2: {NB: 1.0}}}
    symbols = {
        C1: {OCN_ADDR: OCN_SYMB, H2O_ADDR: H2O_SYMB},
        C2: {OCN_ADDR2: OCN_SYMB, H2O_ADDR2: H2O_SYMB},
    }

    target_rewards_per_lp = {C1: {LP1: 10.0}, C2: {LP1: 10.0}}
    target_rewards_info = {C1: {NA: {LP1: 10.0}}, C2: {NB: {LP1: 10.0}}}

    OCEAN_avail = 20.0

    rewards_per_lp, rewards_info = calc_rewards_(
        stakes, locked_amts, nftvols, OCEAN_avail, symbols=symbols
    )

    assert rewards_per_lp == target_rewards_per_lp
    assert rewards_info == target_rewards_info

    # now, make it so that Ocean token in C2 is MOCEAN
    symbols[C2][OCN_ADDR2] = "MOCEAN"
    rewards_per_lp, rewards_info = calc_rewards_(
        stakes, locked_amts, nftvols, OCEAN_avail, symbols=symbols
    )

    assert rewards_per_lp == {C1: {LP1: 20.0}}  # it completely ignores C2's MOCEAN ...
    assert rewards_info == {
        C1: {NA: {LP1: 20.0}}
    }  # ...but of course we don't want that...

    # ... so here's the intervention needed!
    rates = RATES.copy()
    rates["MOCEAN"] = rates["OCEAN"]

    rewards_per_lp, rewards_info = calc_rewards_(
        stakes, locked_amts, nftvols, OCEAN_avail, rates=rates, symbols=symbols
    )

    # now the rewards should line up as expected
    assert rewards_per_lp == target_rewards_per_lp
    assert rewards_info == target_rewards_info


@patch(QUERY_PATH, MagicMock(return_value={}))
@enforce_types
def test_two_lps_simple():
    stakes = {C1: {NA: {LP1: 100e3, LP2: 100e3}}}
    nftvols = {C1: {OCN_ADDR: {NA: 1.0}}}

    OCEAN_avail = 10.0
    rewards_per_lp, rewards_info = calc_rewards_C1(stakes, nftvols, OCEAN_avail)

    assert sum(rewards_per_lp.values()) == pytest.approx(10.0, 0.01)
    assert sum(rewards_info[NA].values()) == pytest.approx(10.0, 0.01)
    assert rewards_per_lp == {LP1: 5.0, LP2: 5.0}
    assert rewards_info == {NA: {LP1: 5.0, LP2: 5.0}}


@patch(QUERY_PATH, MagicMock(return_value={}))
@enforce_types
def test_two_lps_one_with_negligible_stake():
    stakes = {C1: {NA: {LP1: 10e3, LP2: 1e-14 * 10e3}}}
    nftvols = {C1: {OCN_ADDR: {NA: 1.0}}}
    OCEAN_avail = 10.0

    rewards_per_lp, rewards_info = calc_rewards_C1(stakes, nftvols, OCEAN_avail)

    assert sum(rewards_per_lp.values()) == pytest.approx(10.0, 1e-5)
    assert LP2 not in rewards_per_lp

    assert rewards_info[NA][LP1] == pytest.approx(10.0, 1e-6)
    assert LP2 not in rewards_info[NA]


@patch(QUERY_PATH, MagicMock(return_value={}))
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

    rewards_per_lp, rewards_info = calc_rewards_C1(stakes, nftvols, OCEAN_avail)

    assert sum(rewards_per_lp.values()) == pytest.approx(10.0, 0.01)
    assert min(rewards_per_lp.values()) > 0, "shouldn't have entries with 0 rewards"
    assert rewards_per_lp == {LP1: 5.0, LP2: 5.0}

    assert sum(rewards_info[NA].values()) == pytest.approx(10.0, 0.01)
    assert min(rewards_info[NA].values()) > 0, "shouldn't have entries with 0 rewards"
    assert rewards_info == {NA: {LP1: 5.0, LP2: 5.0}}


@patch(QUERY_PATH, MagicMock(return_value={}))
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

    rewards_per_lp, rewards_info = calc_rewards_C1(stakes, nftvols, OCEAN_avail)

    assert sum(rewards_per_lp.values()) == pytest.approx(10.0, 0.01)
    assert rewards_per_lp[LP1] == rewards_per_lp[LP2]
    assert rewards_per_lp[LP1] == rewards_per_lp[LP3]
    assert rewards_per_lp[LP2] == rewards_per_lp[LP3]

    assert sum(rewards_info[NA].values()) == pytest.approx(5.0, 0.01)
    assert sum(rewards_info[NB].values()) == pytest.approx(5.0, 0.01)
    assert rewards_info[NA][LP1] == approx(10 / 3 / 2)
    assert rewards_info[NB][LP1] == approx(10 / 3 / 2)
    assert rewards_info[NA][LP2] == approx(10 / 3)
    assert rewards_info[NB][LP3] == approx(10 / 3)


@patch(QUERY_PATH, MagicMock(return_value={}))
@enforce_types
def test_two_LPs__one_NFT__one_LP_created():
    # LP1 created NA, so it gets 2x equivalent stake on that
    stakes = {C1: {NA: {LP1: 50e3, LP2: 100e3}}}
    nftvols = {C1: {OCN_ADDR: {NA: 1.0}}}
    owners = {C1: {NA: LP1}}

    OCEAN_avail = 10.0
    rewards_per_lp, rewards_info = calc_rewards_C1(
        stakes, nftvols, OCEAN_avail, owners=owners, do_pubrewards=True
    )

    assert sum(rewards_per_lp.values()) == pytest.approx(10.0, 0.01)
    assert sum(rewards_info[NA].values()) == pytest.approx(10.0, 0.01)
    assert rewards_per_lp == {LP1: 5.0, LP2: 5.0}
    assert rewards_info == {NA: {LP1: 5.0, LP2: 5.0}}


@patch(QUERY_PATH, MagicMock(return_value={}))
@enforce_types
def test_two_LPs__two_NFTs__one_LP_created_one_NFT():
    # LP1 created NA, so it gets 2x equivalent stake on NA (but not NB)
    stakes = {C1: {NA: {LP1: 50e3, LP2: 100e3}, NB: {LP1: 100e3, LP2: 100e3}}}
    nftvols = {C1: {OCN_ADDR: {NA: 1.0, NB: 1.0}}}
    owners = {C1: {NA: LP1, NB: ZERO_ADDRESS}}

    OCEAN_avail = 10.0
    rewards_per_lp, rewards_info = calc_rewards_C1(
        stakes, nftvols, OCEAN_avail, owners=owners, do_pubrewards=True
    )

    assert sum(rewards_per_lp.values()) == pytest.approx(10.0, 0.01)
    assert sum(rewards_info[NA].values()) == pytest.approx(5.0, 0.01)
    assert rewards_per_lp == {LP1: 5.0, LP2: 5.0}
    assert rewards_info == {NA: {LP1: 2.5, LP2: 2.5}, NB: {LP1: 2.5, LP2: 2.5}}


@patch(QUERY_PATH, MagicMock(return_value={}))
@enforce_types
def test_two_LPs__two_NFTs__two_LPs_created():
    # LP1 created NA, LP2 created NB, they each get 2x equivalent stake
    stakes = {C1: {NA: {LP1: 50e3, LP2: 100e3}, NB: {LP1: 100e3, LP2: 50e3}}}
    nftvols = {C1: {OCN_ADDR: {NA: 1.0, NB: 1.0}}}
    owners = {C1: {NA: LP1, NB: LP2}}

    OCEAN_avail = 10.0
    rewards_per_lp, rewards_info = calc_rewards_C1(
        stakes, nftvols, OCEAN_avail, owners=owners, do_pubrewards=True
    )

    assert sum(rewards_per_lp.values()) == pytest.approx(10.0, 0.01)
    assert sum(rewards_info[NA].values()) == pytest.approx(5.0, 0.01)
    assert rewards_per_lp == {LP1: 5.0, LP2: 5.0}
    assert rewards_info == {NA: {LP1: 2.5, LP2: 2.5}, NB: {LP1: 2.5, LP2: 2.5}}


@patch(QUERY_PATH, MagicMock(return_value={}))
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

    target_rewards_per_lp = {C1: {LP1: 10.0}}
    target_rewards_info = {C1: {NA: {LP1: 10.0}}}
    OCEAN_avail = 10.0

    # tests
    rewards_per_lp, rewards_info = calc_rewards_(
        stakes2a, stakes2a, nftvols, OCEAN_avail
    )
    assert target_rewards_per_lp == rewards_per_lp
    assert target_rewards_info == rewards_info

    rewards_per_lp, _ = calc_rewards_(stakes2b, stakes2b, nftvols, OCEAN_avail)
    assert target_rewards_per_lp == rewards_per_lp
    assert target_rewards_info == rewards_info

    rewards_per_lp, _ = calc_rewards_(stakes2c, stakes2c, nftvols, OCEAN_avail)
    assert target_rewards_per_lp == rewards_per_lp
    assert target_rewards_info == rewards_info

    rewards_per_lp, _ = calc_rewards_(stakes, stakes, nftvols2a, OCEAN_avail)
    assert target_rewards_per_lp == rewards_per_lp
    assert target_rewards_info == rewards_info

    rewards_per_lp, _ = calc_rewards_(stakes, stakes, nftvols2b, OCEAN_avail)
    assert target_rewards_per_lp == rewards_per_lp
    assert target_rewards_info == rewards_info

    rewards_per_lp, _ = calc_rewards_(
        stakes, stakes, nftvols, OCEAN_avail, rates=rates2
    )
    assert target_rewards_per_lp == rewards_per_lp
    assert target_rewards_info == rewards_info


@patch(QUERY_PATH, MagicMock(return_value={}))
def testcalc_rewards__math():
    ## update this test when the reward function is changed
    stakes = {C1: {NA: {LP1: 1.0e6, LP2: 9.0e6}, NB: {LP3: 10.0e6, LP4: 90.0e6}}}
    nftvols = {C1: {OCN_ADDR: {NA: 0.5e6, NB: 0.5e6}}}
    OCEAN_avail = 5000.0

    rewards_per_lp, _ = calc_rewards_C1(stakes, nftvols, OCEAN_avail)

    assert sum(rewards_per_lp.values()) == pytest.approx(OCEAN_avail, 0.01)

    assert rewards_per_lp[LP1] == pytest.approx(250.0, 0.01)
    assert rewards_per_lp[LP2] == pytest.approx(2250.0, 0.01)
    assert rewards_per_lp[LP3] == pytest.approx(250.0, 0.01)
    assert rewards_per_lp[LP4] == pytest.approx(2250.0, 0.01)


@patch(QUERY_PATH, MagicMock(return_value={}))
@enforce_types
def test_bound_APY_one_nft():
    stakes = {C1: {NA: {LP1: 1.0}}}
    nftvols = {C1: {OCN_ADDR: {NA: 1.0}}}
    OCEAN_avail = 10000.0

    rewards_per_lp, rewards_info = calc_rewards_C1(stakes, nftvols, OCEAN_avail)

    assert rewards_per_lp == {LP1: 1.0 * TARGET_WPY}
    assert rewards_info == {NA: {LP1: 1.0 * TARGET_WPY}}


@patch(QUERY_PATH, MagicMock(return_value={}))
@enforce_types
def test_bound_APY_one_LP__high_stake__two_nfts():
    stakes = {C1: {NA: {LP1: 1e6}, NB: {LP1: 1e6}}}
    nftvols = {C1: {OCN_ADDR: {NA: 1.0, NB: 1.0}}}
    OCEAN_avail = 1000.0

    rewards_per_lp, rewards_info = calc_rewards_C1(stakes, nftvols, OCEAN_avail)

    # ensure that total rewards given doesn't exceed OCEAN_avail
    assert rewards_per_lp == {LP1: 1000.0}
    assert rewards_info == {NA: {LP1: 500.0}, NB: {LP1: 500.0}}


@patch(QUERY_PATH, MagicMock(return_value={}))
@enforce_types
def test_bound_APY_two_nfts__equal_low_stake__equal_low_DCV():
    stakes = {C1: {NA: {LP1: 5.0}, NB: {LP2: 5.0}}}
    nftvols = {C1: {OCN_ADDR: {NA: 1.0, NB: 1.0}}}
    OCEAN_avail = 10000.0

    rewards_per_lp, rewards_info = calc_rewards_C1(stakes, nftvols, OCEAN_avail)

    assert rewards_per_lp == {LP1: 5.0 * TARGET_WPY, LP2: 5.0 * TARGET_WPY}
    assert rewards_info == {NA: {LP1: 5.0 * TARGET_WPY}, NB: {LP2: 5.0 * TARGET_WPY}}


@patch(QUERY_PATH, MagicMock(return_value={}))
@enforce_types
def test_bound_APY_two_nfts__both_low_stake__one_nft_dominates_stake():
    stakes = {C1: {NA: {LP1: 5.0}, NB: {LP2: 20000.0}}}
    nftvols = {C1: {OCN_ADDR: {NA: 1.0, NB: 1.0}}}
    OCEAN_avail = 10000.0

    rewards_per_lp, rewards_info = calc_rewards_C1(stakes, nftvols, OCEAN_avail)

    # LP1 and LP2 each have stake sufficiently low that TARGET_WPY bounds it.
    # But, LP2 staked more, so it earns more
    assert rewards_per_lp == {LP1: 5.0 * TARGET_WPY, LP2: 20000.0 * TARGET_WPY}
    assert rewards_info == {
        NA: {LP1: 5.0 * TARGET_WPY},
        NB: {LP2: 20000 * TARGET_WPY},
    }


@patch(QUERY_PATH, MagicMock(return_value={}))
@enforce_types
def test_bound_APY_two_nfts__low_stake__one_nft_dominates_DCV():
    stakes = {C1: {NA: {LP1: 5.0}, NB: {LP2: 5.0}}}
    nftvols = {C1: {OCN_ADDR: {NA: 1.0, NB: 10000.0}}}
    OCEAN_avail = 10000.0

    rewards_per_lp, rewards_info = calc_rewards_C1(stakes, nftvols, OCEAN_avail)

    # LP1 and LP2 get same amount - they're both bounded because both have low stake
    # Critically, LP2 doesn't swamp LP1 just because LP2's stake * DCV is way higher
    assert rewards_per_lp == {LP1: 5.0 * TARGET_WPY, LP2: 5.0 * TARGET_WPY}
    assert rewards_info == {NA: {LP1: 5.0 * TARGET_WPY}, NB: {LP2: 5.0 * TARGET_WPY}}


@patch(QUERY_PATH, MagicMock(return_value={}))
@enforce_types
def test_bound_APY_two_nfts__high_stake__one_nft_dominates_DCV():
    stakes = {C1: {NA: {LP1: 1e6}, NB: {LP2: 1e6}}}
    nftvols = {C1: {OCN_ADDR: {NA: 1.0, NB: 9999.0}}}
    OCEAN_avail = 10000.0

    rewards_per_lp, rewards_info = calc_rewards_C1(stakes, nftvols, OCEAN_avail)

    # LP2 reward swamps LP1 because LP2's stake * DCV is way higher
    assert rewards_per_lp == {LP1: 1.0, LP2: 9999.0}
    assert rewards_info == {NA: {LP1: 1.0}, NB: {LP2: 9999.0}}


@patch(QUERY_PATH, MagicMock(return_value={}))
@enforce_types
def test_bound_by_DCV_1nft_1account():
    DCV_OCEAN = 100.0

    stakes = {C1: {NA: {LP1: 1e6}}}
    nftvols = {C1: {OCN_ADDR: {NA: DCV_OCEAN}}}
    OCEAN_avail = 10000.0

    # df week = 9 -> DCV multiplier = 1.0
    rewards_per_lp, rewards_info = calc_rewards_C1(
        stakes, nftvols, OCEAN_avail, df_week=9
    )
    assert rewards_per_lp == {LP1: 100.0}
    assert rewards_info == {NA: {LP1: 100.0}}

    with patch("df_py.volume.reward_calculator.calc_dcv_multiplier") as mock_mult:
        mock_mult.return_value = 0.5
        rewards_per_lp, rewards_info = calc_rewards_C1(stakes, nftvols, OCEAN_avail)
    assert rewards_per_lp == {LP1: 50.0}
    assert rewards_info == {NA: {LP1: 50.0}}


@patch(QUERY_PATH, MagicMock(return_value={}))
@enforce_types
def test_bound_by_DCV_1nft_2accounts():
    DCV_OCEAN = 100.0

    stakes = {C1: {NA: {LP1: 0.5e6, LP2: 0.5e6}}}
    nftvols = {C1: {OCN_ADDR: {NA: DCV_OCEAN}}}
    OCEAN_avail = 10000.0

    with patch("df_py.volume.reward_calculator.calc_dcv_multiplier") as mock_mult:
        mock_mult.return_value = 0.5
        rewards_per_lp, _ = calc_rewards_C1(stakes, nftvols, OCEAN_avail)
    assert rewards_per_lp == {LP1: 25.0, LP2: 25.0}


@enforce_types
def test_custom_multipliers():
    DCV_OCEAN = 100.0

    stakes = {C1: {NA: {LP1: 1e6}}}
    nftvols = {C1: {OCN_ADDR: {NA: DCV_OCEAN}}}
    OCEAN_avail = 10000.0

    with patch(
        "df_py.volume.reward_calculator.query_predictoor_contracts"
    ) as mock, patch(
        "df_py.volume.reward_calculator.DEPLOYER_ADDRS",
        {C1: ""},
    ):
        mock.return_value = {NA: ""}
        rewards_per_lp, rewards_info = calc_rewards_C1(
            stakes,
            nftvols,
            OCEAN_avail,
        )

    assert rewards_per_lp == {LP1: 100.0 * 0.201}
    assert rewards_info == {NA: {LP1: 100.0 * 0.201}}


@patch(QUERY_PATH, MagicMock(return_value={}))
@enforce_types
def test_divide_by_zero():
    stakes = {C1: {NA: {LP1: 10000.0}, NB: {LP2: 10000.0}}}
    nftvols = {C1: {OCN_ADDR: {LP1: 0, LP2: 0}}}
    OCEAN_avail = 10000.0

    rewards_per_lp, _ = calc_rewards_C1(stakes, nftvols, OCEAN_avail)

    # Should return empty dict because LP1 and LP2 have zero volume
    assert rewards_per_lp == {}


# ========================================================================
# Test helper functions found in calc_rewards


@enforce_types
def test_get_nft_addrs():
    nftvols_USD = {C1: {NA: 1.0, NB: 1.0}, C2: {NC: 1.0}}
    mock_calculator = MockRewardCalculator()
    mock_calculator.set_mock_attribute("nftvols_USD", nftvols_USD)
    nft_addrs = mock_calculator._get_nft_addrs()
    assert isinstance(nft_addrs, list)
    assert sorted(nft_addrs) == sorted([NA, NB, NC])


@enforce_types
def test_get_lp_addrs():
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
    mock_calculator = MockRewardCalculator()
    mock_calculator.set_mock_attribute("stakes", stakes)
    LP_addrs = mock_calculator._get_lp_addrs()
    assert isinstance(LP_addrs, list)
    assert sorted(LP_addrs) == sorted([LP1, LP2, LP3, LP4])


@enforce_types
def test_stake_vol_owner_dicts_to_arrays():
    # define the inputs for the function
    stakes = {
        1: {
            NA: {LP1: 10.0, LP2: 20.0},
            NB: {LP1: 30.0, LP2: 40.0},
        },
        2: {
            NC: {LP3: 50.0, LP4: 60.0},
            ND: {LP3: 70.0, LP4: 80.0},
        },
    }
    locked_ocean_amts = {
        1: {
            NA: {LP1: 10.0, LP2: 20.0},
            NB: {LP1: 30.0, LP2: 40.0},
        },
        2: {
            NC: {LP3: 50.0, LP4: 60.0},
            ND: {LP3: 70.0, LP4: 80.0},
        },
    }
    nftvols_USD = {
        1: {NA: 15.0, NB: 25.0},
        2: {NC: 35.0, ND: 45.0},
    }
    lp_addrs = [LP1, LP2, LP3, LP4]
    chain_nft_tups = [(1, NA), (1, NB), (2, NC), (2, ND)]

    mock_calculator = MockRewardCalculator()
    mock_calculator.set_mock_attribute("stakes", stakes)
    mock_calculator.set_mock_attribute("locked_ocean_amts", locked_ocean_amts)
    mock_calculator.set_mock_attribute("nftvols_USD", nftvols_USD)
    mock_calculator.set_mock_attribute("LP_addrs", lp_addrs)
    mock_calculator.set_mock_attribute("chain_nft_tups", chain_nft_tups)
    mock_calculator.set_mock_attribute("predictoor_feed_addrs", {1: "", 2: ""})

    owners = null_owners_from_chain_nft_tups(chain_nft_tups)
    mock_calculator.set_mock_attribute("owners", owners)

    S, V_USD, _, _, L = mock_calculator._stake_vol_owner_dicts_to_arrays()

    expected_S = np.array(
        [
            [10.0, 30.0, 0.0, 0.0],
            [20.0, 40.0, 0.0, 0.0],
            [0.0, 0.0, 50.0, 70.0],
            [0.0, 0.0, 60.0, 80.0],
        ],
        dtype=float,
    )
    expected_L = np.array(
        [
            [10.0, 30.0, 0.0, 0.0],
            [20.0, 40.0, 0.0, 0.0],
            [0.0, 0.0, 50.0, 70.0],
            [0.0, 0.0, 60.0, 80.0],
        ],
        dtype=float,
    )
    expected_V_USD = np.array([15.0, 25.0, 35.0, 45.0], dtype=float)

    assert np.array_equal(S, expected_S)
    assert np.array_equal(L, expected_L)
    assert np.array_equal(V_USD, expected_V_USD)


@enforce_types
def test_volume_reward_calculator_no_pdrs(tmp_path):
    stakes = {
        C1: {NA: {LP1: 1e8}},
        C2: {NB: {LP2: 1e8, LP3: 2e8}},
    }
    locked_amts = {
        C1: {NA: {LP1: 1e8}},
        C2: {NB: {LP2: 1e8, LP3: 2e8}},
    }
    volumes = {
        C1: {OCN_ADDR: {NA: 300.0}},
        C2: {H2O_ADDR: {NB: 600.0}},
    }
    owners = {C1: {NA: LP1}, C2: {NB: LP2}}
    symbols = {C1: {OCN_ADDR: OCN_SYMB}, C2: {H2O_ADDR: H2O_SYMB}}
    rates = {OCN_SYMB: 1.0, H2O_SYMB: 1.0}
    multiplier = 1.0
    OCEAN_reward = 1000.0

    with patch(
        "df_py.volume.allocations.load_stakes",
        return_value=(stakes, locked_amts),
    ), patch("df_py.volume.csvs.load_nftvols_csvs", return_value=volumes), patch(
        "df_py.volume.csvs.load_owners_csvs", return_value=owners
    ), patch(
        "df_py.volume.csvs.load_symbols_csvs", return_value=symbols
    ), patch(
        "df_py.volume.csvs.load_rate_csvs", return_value=rates
    ), patch(
        "df_py.volume.reward_calculator.calc_dcv_multiplier",
        return_value=multiplier,
    ), patch(
        "df_py.util.dcv_multiplier.get_df_week_number", return_value=30
    ), patch(
        "df_py.volume.reward_calculator.query_predictoor_contracts",
        return_value={C1: "", C2: ""},
    ), patch(
        "df_py.volume.calc_rewards.wait_to_latest_block"
    ), patch(
        "web3.main.Web3.to_checksum_address"
    ) as mock:
        mock.side_effect = lambda value: value

        calc_volume_rewards_from_csvs(tmp_path, None, OCEAN_reward, True, False)

        rewards_per_lp = csvs.load_volume_rewards_csv(str(tmp_path))

        # OCEAN_reward was 1000
        # volumes were 300 (NA) & 600 (NB), for 900 total
        # Since fee multiplier is 1.0, DCV bound is 300 for NA, 600 for NB
        # Therefore DCV bound is the constraint on rewards
        # Therefore 300 OCEAN goes to NA, 600 goes to NB

        # NA's LPs are {LP1}, therefore LP1 gets all 300 OCEAN
        assert rewards_per_lp[C1][LP1] == 300

        # NB's LPs are {LP2, LP3}, so they split the 600 OCEAN
        #   LP2 has 1/2 the stake, but gets a 2x for publishing. Result=equal
        assert rewards_per_lp[C2][LP2] == 300
        assert rewards_per_lp[C2][LP3] == 300

        rewards_info = csvs.load_volume_rewardsinfo_csv(str(tmp_path))
        assert rewards_info[C1][NA][LP1] == 300
        assert rewards_info[C2][NB][LP2] == 300
        assert rewards_info[C2][NB][LP3] == 300


@enforce_types
def test_volume_reward_calculator_pdr_mul(tmp_path):
    stakes = {
        C1: {NA: {LP1: 2e8}},
        C2: {NB: {LP2: 1e8, LP3: 2e8}},
    }
    locked_amts = {
        C1: {NA: {LP1: 1e8}},
        C2: {NB: {LP2: 1e8, LP3: 2e8}},
    }
    volumes = {
        C1: {OCN_ADDR: {NA: 300.0}},
        C2: {H2O_ADDR: {NB: 600.0}},
    }
    owners = {C1: {NA: LP5}, C2: {NB: LP2}}
    symbols = {C1: {OCN_ADDR: OCN_SYMB}, C2: {H2O_ADDR: H2O_SYMB}}
    rates = {OCN_SYMB: 1.0, H2O_SYMB: 1.0}

    predictoor_contracts = {NA: {}}

    def mock_multipliers(DF_week, is_predictoor):  # pylint: disable=unused-argument
        if not is_predictoor:
            return MagicMock(return_value=1)
        return 0.201

    OCEAN_reward = 1000.0

    with patch(
        "df_py.volume.allocations.load_stakes",
        return_value=(stakes, locked_amts),
    ), patch("df_py.volume.csvs.load_nftvols_csvs", return_value=volumes), patch(
        "df_py.volume.csvs.load_owners_csvs", return_value=owners
    ), patch(
        "df_py.volume.csvs.load_symbols_csvs", return_value=symbols
    ), patch(
        "df_py.volume.csvs.load_rate_csvs", return_value=rates
    ), patch(
        "df_py.volume.reward_calculator.calc_dcv_multiplier", mock_multipliers
    ), patch(
        "df_py.volume.reward_calculator.query_predictoor_contracts",
        return_value=predictoor_contracts,
    ), patch(
        "df_py.volume.reward_calculator.DEPLOYER_ADDRS",
        {C1: ""},
    ), patch(
        "df_py.util.dcv_multiplier.get_df_week_number", return_value=30
    ), patch(
        "df_py.volume.calc_rewards.wait_to_latest_block"
    ), patch(
        "web3.main.Web3.to_checksum_address"
    ) as mock:
        mock.side_effect = lambda value: value

        calc_volume_rewards_from_csvs(tmp_path, None, OCEAN_reward, True, False)

        rewards_per_lp = csvs.load_volume_rewards_csv(str(tmp_path))

        # OCEAN_reward was 1000
        # volumes were 300 (NA) & 600 (NB), for 900 total
        # NA is a predictoor asset
        #   --> gets fee multiplier 0.201
        #   --> DCV bound = 300 * 0.201 = 60.3
        # NB isn't a predictoor asset
        #   --> gets fee multiplier 1.0
        #   --> DCV bound = 600 * 1.0 = 600.0
        # DCV bound is the constraint on rewards
        # Therefore 60.3 OCEAN goes to NA, 600 goes to NB

        # NA's LPs are {LP1}, therefore LP1 gets all 300 OCEAN
        assert rewards_per_lp[C1][LP1] == approx(60.3, abs=1e-5)

        # NB's LPs are {LP2, LP3}, so they split the 600 OCEAN
        #   LP2 has 1/2 the stake, but gets a 2x for publishing. Result=equal
        assert rewards_per_lp[C2][LP2] == 300
        assert rewards_per_lp[C2][LP3] == 300

        rewards_info = csvs.load_volume_rewardsinfo_csv(str(tmp_path))
        assert rewards_info[C1][NA][LP1] == approx(60.3, abs=1e-5)
        assert rewards_info[C2][NB][LP2] == 300
        assert rewards_info[C2][NB][LP3] == 300


@enforce_types
def test_volume_reward_calculator_pdr_boost(tmp_path):
    SAPPHIRE_MAINNET = 23294
    stakes = {
        SAPPHIRE_MAINNET: {NA: {LP1: 2e8}, NB: {LP2: 1e8}},
    }
    locked_amts = {
        SAPPHIRE_MAINNET: {NA: {LP1: 1e8}, NB: {LP2: 1e8}},
    }
    volumes = {
        SAPPHIRE_MAINNET: {
            OCN_ADDR: {
                NA: PREDICTOOR_OCEAN_BUDGET / 2 - 1,
                NB: PREDICTOOR_OCEAN_BUDGET * 2,
            }
        },
    }
    owners = {SAPPHIRE_MAINNET: {NA: LP5, NB: LP2}}
    symbols = {SAPPHIRE_MAINNET: {OCN_ADDR: OCN_SYMB}}
    rates = {OCN_SYMB: 1.0}

    predictoor_contracts = {NA: {}, NB: {}}

    def mock_multipliers(DF_week, is_predictoor):  # pylint: disable=unused-argument
        if not is_predictoor:
            return MagicMock(return_value=1)
        return 0.201

    OCEAN_reward = 1e24

    with patch(
        "df_py.volume.allocations.load_stakes",
        return_value=(stakes, locked_amts),
    ), patch("df_py.volume.csvs.load_nftvols_csvs", return_value=volumes), patch(
        "df_py.volume.csvs.load_owners_csvs", return_value=owners
    ), patch(
        "df_py.volume.csvs.load_symbols_csvs", return_value=symbols
    ), patch(
        "df_py.volume.csvs.load_rate_csvs", return_value=rates
    ), patch(
        "df_py.volume.reward_calculator.calc_dcv_multiplier", mock_multipliers
    ), patch(
        "df_py.volume.reward_calculator.query_predictoor_contracts",
        return_value=predictoor_contracts,
    ), patch(
        "df_py.volume.reward_calculator.DEPLOYER_ADDRS",
        {SAPPHIRE_MAINNET: ""},
    ), patch(
        "df_py.util.dcv_multiplier.get_df_week_number", return_value=30
    ), patch(
        "df_py.volume.calc_rewards.wait_to_latest_block"
    ), patch(
        "web3.main.Web3.to_checksum_address"
    ) as mock:
        mock.side_effect = lambda value: value

        calc_volume_rewards_from_csvs(tmp_path, None, OCEAN_reward, True, False)

        rewards_per_lp = csvs.load_volume_rewards_csv(str(tmp_path))

        # OCEAN_reward was 1e24, it's a lot so it's not a constraint
        # The predictoor boost per asset is limited at PREDICTOOR_BUDGET / 2
        # NA and NB are predictoor assets

        # NA has PREDICTOOR_OCEAN_BUDGET / 2 - 2 volume
        #   --> since the volume is smaller than boost limit, all DCV is boosted to 5x
        #   --> DCV bound = (PREDICTOOR_BUDGET / 2 - 1) * 0.201 * 5

        # NB has PREDICTOOR_BUDGET * 2 volume
        # Thus only the volume up to the budget is boosted
        #   --> DCV bound = PREDICTOOR_BUDGET / 2 * 0.201 * 5 + (PREDICTOOR_BUDGET / 2) * 0.201

        vol1 = PREDICTOOR_OCEAN_BUDGET / 2 - 1
        boosted = vol1 * 0.201 * 5
        assert rewards_per_lp[SAPPHIRE_MAINNET][LP1] == approx(boosted, abs=1e-5)

        vol2 = PREDICTOOR_OCEAN_BUDGET * 2
        boosted_amt = (
            PREDICTOOR_OCEAN_BUDGET / 2
        )  # divided by 2 because 2 predictoor assets
        boosted = (boosted_amt) * 0.201 * 5  # 5x boost
        remaining_dcv = (vol2 - boosted_amt) * 0.201
        assert rewards_per_lp[SAPPHIRE_MAINNET][LP2] == approx(
            boosted + remaining_dcv, abs=1e-5
        )
