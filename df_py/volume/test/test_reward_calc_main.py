from datetime import datetime, timedelta
from typing import Dict, List, Tuple, Union
from unittest.mock import MagicMock, patch

import numpy as np
import pytest
from enforce_typing import enforce_types
from pytest import approx

from df_py.volume.reward_calc_main import TARGET_WPY, RewardCalculator
from df_py.volume.reward_calc_wrapper import calc_volume_rewards_from_csvs
from df_py.web3util.constants import ZERO_ADDRESS


@patch(
    "df_py.queries.predictoor_queries.query_predictoor_contracts",
    MagicMock(return_value={}),
)
@enforce_types
def test_simple():
    stakes = {C1: {NA: {LP1: 1000.0}}}
    locked_amts = {C1: {NA: {LP1: 1000.0}}}
    nftvols = {C1: {OCN_ADDR: {NA: 1.0}}}
    OCEAN_avail = 10.0

    rewards_per_lp, rewards_info = _calc_rewards(
        stakes, locked_amts, nftvols, OCEAN_avail
    )
    assert rewards_per_lp == {C1: {LP1: 10.0}}
    assert rewards_info == {C1: {NA: {LP1: 10}}}

    # test helper - just C1
    rewards_per_lp, rewards_info = calc_rewards_C1(stakes, nftvols, OCEAN_avail)
    assert rewards_per_lp == {LP1: 10.0}
    assert rewards_info == {NA: {LP1: 10}}


@patch(
    "df_py.queries.predictoor_queries.query_predictoor_contracts",
    MagicMock(return_value={}),
)
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


@patch(
    "df_py.queries.predictoor_queries.query_predictoor_contracts",
    MagicMock(return_value={}),
)
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

    rewards_per_lp, rewards_info = _calc_rewards(
        stakes, locked_amts, nftvols, OCEAN_avail, symbols=symbols
    )

    assert rewards_per_lp == target_rewards_per_lp
    assert rewards_info == target_rewards_info

    # now, make it so that Ocean token in C2 is MOCEAN
    symbols[C2][OCN_ADDR2] = "MOCEAN"
    rewards_per_lp, rewards_info = _calc_rewards(
        stakes, locked_amts, nftvols, OCEAN_avail, symbols=symbols
    )

    assert rewards_per_lp == {C1: {LP1: 20.0}}  # it completely ignores C2's MOCEAN ...
    assert rewards_info == {
        C1: {NA: {LP1: 20.0}}
    }  # ...but of course we don't want that...

    # ... so here's the intervention needed!
    rates = RATES.copy()
    rates["MOCEAN"] = rates["OCEAN"]

    rewards_per_lp, rewards_info = _calc_rewards(
        stakes, locked_amts, nftvols, OCEAN_avail, rates=rates, symbols=symbols
    )

    # now the rewards should line up as expected
    assert rewards_per_lp == target_rewards_per_lp
    assert rewards_info == target_rewards_info


@patch(
    "df_py.queries.predictoor_queries.query_predictoor_contracts",
    MagicMock(return_value={}),
)
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


@patch(
    "df_py.queries.predictoor_queries.query_predictoor_contracts",
    MagicMock(return_value={}),
)
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


@patch(
    "df_py.queries.predictoor_queries.query_predictoor_contracts",
    MagicMock(return_value={}),
)
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


@patch(
    "df_py.queries.predictoor_queries.query_predictoor_contracts",
    MagicMock(return_value={}),
)
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


@patch(
    "df_py.queries.predictoor_queries.query_predictoor_contracts",
    MagicMock(return_value={}),
)
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


@patch(
    "df_py.queries.predictoor_queries.query_predictoor_contracts",
    MagicMock(return_value={}),
)
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


@patch(
    "df_py.queries.predictoor_queries.query_predictoor_contracts",
    MagicMock(return_value={}),
)
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


@patch(
    "df_py.queries.predictoor_queries.query_predictoor_contracts",
    MagicMock(return_value={}),
)
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
    rewards_per_lp, rewards_info = _calc_rewards(
        stakes2a, stakes2a, nftvols, OCEAN_avail
    )
    assert target_rewards_per_lp == rewards_per_lp
    assert target_rewards_info == rewards_info

    rewards_per_lp, _ = _calc_rewards(stakes2b, stakes2b, nftvols, OCEAN_avail)
    assert target_rewards_per_lp == rewards_per_lp
    assert target_rewards_info == rewards_info

    rewards_per_lp, _ = _calc_rewards(stakes2c, stakes2c, nftvols, OCEAN_avail)
    assert target_rewards_per_lp == rewards_per_lp
    assert target_rewards_info == rewards_info

    rewards_per_lp, _ = _calc_rewards(stakes, stakes, nftvols2a, OCEAN_avail)
    assert target_rewards_per_lp == rewards_per_lp
    assert target_rewards_info == rewards_info

    rewards_per_lp, _ = _calc_rewards(stakes, stakes, nftvols2b, OCEAN_avail)
    assert target_rewards_per_lp == rewards_per_lp
    assert target_rewards_info == rewards_info

    rewards_per_lp, _ = _calc_rewards(
        stakes, stakes, nftvols, OCEAN_avail, rates=rates2
    )
    assert target_rewards_per_lp == rewards_per_lp
    assert target_rewards_info == rewards_info


@patch(
    "df_py.queries.predictoor_queries.query_predictoor_contracts",
    MagicMock(return_value={}),
)
def test_calc_rewards_math():
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


@patch(
    "df_py.queries.predictoor_queries.query_predictoor_contracts",
    MagicMock(return_value={}),
)
@enforce_types
def test_bound_APY_one_nft():
    stakes = {C1: {NA: {LP1: 1.0}}}
    nftvols = {C1: {OCN_ADDR: {NA: 1.0}}}
    OCEAN_avail = 10000.0

    rewards_per_lp, rewards_info = calc_rewards_C1(stakes, nftvols, OCEAN_avail)

    assert rewards_per_lp == {LP1: 1.0 * TARGET_WPY}
    assert rewards_info == {NA: {LP1: 1.0 * TARGET_WPY}}


@patch(
    "df_py.queries.predictoor_queries.query_predictoor_contracts",
    MagicMock(return_value={}),
)
@enforce_types
def test_bound_APY_one_LP__high_stake__two_nfts():
    stakes = {C1: {NA: {LP1: 1e6}, NB: {LP1: 1e6}}}
    nftvols = {C1: {OCN_ADDR: {NA: 1.0, NB: 1.0}}}
    OCEAN_avail = 1000.0

    rewards_per_lp, rewards_info = calc_rewards_C1(stakes, nftvols, OCEAN_avail)

    # ensure that total rewards given doesn't exceed OCEAN_avail
    assert rewards_per_lp == {LP1: 1000.0}
    assert rewards_info == {NA: {LP1: 500.0}, NB: {LP1: 500.0}}


@patch(
    "df_py.queries.predictoor_queries.query_predictoor_contracts",
    MagicMock(return_value={}),
)
@enforce_types
def test_bound_APY_two_nfts__equal_low_stake__equal_low_DCV():
    stakes = {C1: {NA: {LP1: 5.0}, NB: {LP2: 5.0}}}
    nftvols = {C1: {OCN_ADDR: {NA: 1.0, NB: 1.0}}}
    OCEAN_avail = 10000.0

    rewards_per_lp, rewards_info = calc_rewards_C1(stakes, nftvols, OCEAN_avail)

    assert rewards_per_lp == {LP1: 5.0 * TARGET_WPY, LP2: 5.0 * TARGET_WPY}
    assert rewards_info == {NA: {LP1: 5.0 * TARGET_WPY}, NB: {LP2: 5.0 * TARGET_WPY}}


@patch(
    "df_py.queries.predictoor_queries.query_predictoor_contracts",
    MagicMock(return_value={}),
)
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


@patch(
    "df_py.queries.predictoor_queries.query_predictoor_contracts",
    MagicMock(return_value={}),
)
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


@patch(
    "df_py.queries.predictoor_queries.query_predictoor_contracts",
    MagicMock(return_value={}),
)
@enforce_types
def test_bound_APY_two_nfts__high_stake__one_nft_dominates_DCV():
    stakes = {C1: {NA: {LP1: 1e6}, NB: {LP2: 1e6}}}
    nftvols = {C1: {OCN_ADDR: {NA: 1.0, NB: 9999.0}}}
    OCEAN_avail = 10000.0

    rewards_per_lp, rewards_info = calc_rewards_C1(stakes, nftvols, OCEAN_avail)

    # LP2 reward swamps LP1 because LP2's stake * DCV is way higher
    assert rewards_per_lp == {LP1: 1.0, LP2: 9999.0}
    assert rewards_info == {NA: {LP1: 1.0}, NB: {LP2: 9999.0}}


@patch(
    "df_py.queries.predictoor_queries.query_predictoor_contracts",
    MagicMock(return_value={}),
)
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

    with patch("df_py.vestingutil.week_multiplier.calc_dcv_multiplier") as mock_dcv:
        mock_dcv.return_value = 0.5
        rewards_per_lp, rewards_info = calc_rewards_C1(stakes, nftvols, OCEAN_avail)
    assert rewards_per_lp == {LP1: 50.0}
    assert rewards_info == {NA: {LP1: 50.0}}


@patch(
    "df_py.queries.predictoor_queries.query_predictoor_contracts",
    MagicMock(return_value={}),
)
@enforce_types
def test_bound_by_DCV_1nft_2accounts():
    DCV_OCEAN = 100.0

    stakes = {C1: {NA: {LP1: 0.5e6, LP2: 0.5e6}}}
    nftvols = {C1: {OCN_ADDR: {NA: DCV_OCEAN}}}
    OCEAN_avail = 10000.0

    with patch("df_py.vestingutil.week_multiplier.calc_dcv_multiplier") as mock_dcv:
        mock_dcv.return_value = 0.5
        rewards_per_lp, _ = calc_rewards_C1(stakes, nftvols, OCEAN_avail)
    assert rewards_per_lp == {LP1: 25.0, LP2: 25.0}


@enforce_types
def test_custom_multipliers():
    DCV_OCEAN = 100.0

    stakes = {C1: {NA: {LP1: 1e6}}}
    nftvols = {C1: {OCN_ADDR: {NA: DCV_OCEAN}}}
    OCEAN_avail = 10000.0

    with patch(
        "df_py.queries.predictoor_queries.query_predictoor_contracts"
    ) as mock, patch(
        "df_py.volume.reward_calc_main.DEPLOYER_ADDRS",
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


@patch(
    "df_py.queries.predictoor_queries.query_predictoor_contracts",
    MagicMock(return_value={}),
)
@enforce_types
def test_divide_by_zero():
    stakes = {C1: {NA: {LP1: 10000.0}, NB: {LP2: 10000.0}}}
    nftvols = {C1: {OCN_ADDR: {LP1: 0, LP2: 0}}}
    OCEAN_avail = 10000.0

    rewards_per_lp, _ = calc_rewards_C1(stakes, nftvols, OCEAN_avail)

    # Should return empty dict because LP1 and LP2 have zero volume
    assert rewards_per_lp == {}
