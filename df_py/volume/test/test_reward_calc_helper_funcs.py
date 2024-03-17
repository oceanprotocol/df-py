# Test calc_rewards.py's helper functions

from enforce_typing import enforce_types
import numpy as np

from df_py.volume.test.conftest import *  # pylint: disable=wildcard-import


@enforce_types
def test_get_nft_addrs():
    mock_calculator = reward_calculator_with_empty_defaults()
    mock_calculator.nftvols_USD = {C1: {NA: 1.0, NB: 1.0}, C2: {NC: 1.0}}
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
    mock_calculator = reward_calculator_with_empty_defaults(stakes=stakes)
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
    mock_calculator = reward_calculator_with_empty_defaults(
        stakes=stakes,
        locked_ocean_amts=locked_ocean_amts,
    )

    mock_calculator.nftvols_USD = {
        1: {NA: 15.0, NB: 25.0},
        2: {NC: 35.0, ND: 45.0},
    }
    mock_calculator.LP_addrs = [LP1, LP2, LP3, LP4]
    mock_calculator.chain_nft_tups = [(1, NA), (1, NB), (2, NC), (2, ND)]
    mock_calculator.predictoor_feed_addrs = {1: "", 2: ""}

    mock_calculator.owners = null_owners_from_chain_nft_tups(
        mock_calculator.chain_nft_tups
    )

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
