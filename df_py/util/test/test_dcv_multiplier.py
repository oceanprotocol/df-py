from datetime import datetime, timedelta

from enforce_typing import enforce_types
import numpy as np
import pytest

from df_py.util.dcv_multiplier import get_df_week_number, calc_dcv_multiplier


@enforce_types
def test_get_df_week_number():
    wk_nbr = get_df_week_number

    # test DF5. Counting starts Thu Sep 29, 2022. Last day is Wed Oct 5, 2022
    assert wk_nbr(datetime(2022, 9, 28)) == -1  # Wed
    assert wk_nbr(datetime(2022, 9, 29)) == 5  # Thu
    assert wk_nbr(datetime(2022, 9, 30)) == 5  # Fri
    assert wk_nbr(datetime(2022, 10, 5)) == 5  # Wed
    assert wk_nbr(datetime(2022, 10, 6)) == 6  # Thu
    assert wk_nbr(datetime(2022, 10, 12)) == 6  # Wed
    assert wk_nbr(datetime(2022, 10, 13)) == 7  # Thu

    # test DF9. Start Thu Oct 27. Last day is Wed Nov 2, 2022,
    assert wk_nbr(datetime(2022, 10, 25)) == 8  # Wed
    assert wk_nbr(datetime(2022, 10, 26)) == 8  # Wed
    assert wk_nbr(datetime(2022, 10, 27)) == 9  # Thu
    assert wk_nbr(datetime(2022, 10, 28)) == 9  # Fri
    assert wk_nbr(datetime(2022, 11, 2)) == 9  # Wed
    assert wk_nbr(datetime(2022, 11, 3)) == 10  # Thu
    assert wk_nbr(datetime(2022, 11, 4)) == 10  # Fri

    # test many weeks
    start_dt = datetime(2022, 9, 29)
    for wks_offset in range(50):
        true_wk = wks_offset + 1 + 4
        assert wk_nbr(start_dt + timedelta(weeks=wks_offset)) == true_wk
        assert wk_nbr(start_dt + timedelta(weeks=wks_offset, days=1)) == true_wk
        assert wk_nbr(start_dt + timedelta(weeks=wks_offset, days=2)) == true_wk
        assert wk_nbr(start_dt + timedelta(weeks=wks_offset, days=3)) == true_wk
        assert wk_nbr(start_dt + timedelta(weeks=wks_offset, days=4)) == true_wk
        assert wk_nbr(start_dt + timedelta(weeks=wks_offset, days=5)) == true_wk
        assert wk_nbr(start_dt + timedelta(weeks=wks_offset, days=6)) == true_wk

    # test extremes
    assert wk_nbr(datetime(2000, 1, 1)) == -1
    assert wk_nbr(datetime(2022, 6, 14)) == -1
    assert wk_nbr(datetime(2022, 6, 15)) == -1
    assert 50 < wk_nbr(datetime(2030, 1, 1)) < 10000
    assert 50 < wk_nbr(datetime(2040, 1, 1)) < 10000


@enforce_types
def test_calc_dcv_multiplier():
    mult = calc_dcv_multiplier

    assert mult(-10, False) == np.inf
    assert mult(-1, False) == np.inf
    assert mult(0, False) == np.inf
    assert mult(1, False) == np.inf
    assert mult(8, False) == np.inf
    assert mult(9, False) == 1.0
    assert mult(10, False) == pytest.approx(0.951, 0.001)
    assert mult(11, False) == pytest.approx(0.903, 0.001)
    assert mult(12, False) == pytest.approx(0.854, 0.001)
    assert mult(20, False) == pytest.approx(0.4665, 0.001)
    assert mult(27, False) == pytest.approx(0.127, 0.001)
    assert mult(28, False) == pytest.approx(0.0785, 0.001)
    assert mult(29, False) == 0.001
    assert mult(30, False) == 0.001
    assert mult(31, False) == 0.001
    assert mult(100, False) == 0.001
    assert mult(10000, False) == 0.001

    assert mult(-10, True) == 0.201
    assert mult(9, True) == 0.201
    assert mult(12, True) == 0.201
    assert mult(10000, True) == 0.201
