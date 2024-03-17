from unittest.mock import MagicMock, patch

from enforce_typing import enforce_types
from pytest import approx

from df_py.volume import csvs
from df_py.volume.reward_calc_wrapper import calc_volume_rewards_from_csvs
from df_py.volume.test.conftest import *  # pylint: disable=wildcard-import
from df_py.web3util.constants import ZERO_ADDRESS


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
        "df_py.volume.reward_calc_main.calc_dcv_multiplier",
        return_value=multiplier,
    ), patch(
        "df_py.volume.reward_calc_main.get_df_week_number", return_value=30
    ), patch(
        "df_py.queries.predictoor_queries.query_predictoor_contracts",
        return_value={C1: "", C2: ""},
    ), patch(
        "df_py.volume.reward_calc_wrapper.wait_to_latest_block"
    ), patch(
        "web3.main.Web3.to_checksum_address"
    ) as mock:
        mock.side_effect = lambda value: value

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

    predictoor_feed_addrs = {C1: [NA], C2: []}

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
        "df_py.volume.reward_calc_main.calc_dcv_multiplier", mock_multipliers
    ), patch(
        "df_py.volume.reward_calc_main.query_predictoor_feed_addrs",
        return_value=predictoor_feed_addrs,
    ), patch(
        "df_py.volume.reward_calc_main.DEPLOYER_ADDRS",
        {C1: ""},
    ), patch(
        "df_py.volume.reward_calc_main.get_df_week_number", return_value=30
    ), patch(
        "df_py.volume.reward_calc_wrapper.wait_to_latest_block"
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
