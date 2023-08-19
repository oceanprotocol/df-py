import datetime
from datetime import timezone

import pytest
from enforce_typing import enforce_types

from df_py.challenge import helpers


@enforce_types
def test_dt_to_ut_timezone():
    # setup
    unaware_dt = datetime.datetime(2011, 8, 15, 8, 15, 12, 0)
    aware_dt = datetime.datetime(2011, 8, 15, 8, 15, 12, 0, tzinfo=timezone.utc)
    now_aware_dt = unaware_dt.replace(tzinfo=timezone.utc)
    assert aware_dt == now_aware_dt

    # can we check tzinfo ?
    assert unaware_dt.tzinfo is None
    assert aware_dt.tzinfo == timezone.utc
    assert now_aware_dt.tzinfo == timezone.utc

    # run dt_to_ut(). unaware_dt should fail, others should pass
    with pytest.raises(Exception) as e_info:
        helpers.dt_to_ut(unaware_dt)
    error_str = str(e_info.value)
    assert error_str == "must be in UTC"

    _ = helpers.dt_to_ut(aware_dt)
    _ = helpers.dt_to_ut(now_aware_dt)


@enforce_types
def test_dt_to_ut_main():
    # time = when unix time starts
    dt = datetime.datetime(1970, 1, 1, 0, 0, 0, 0, tzinfo=timezone.utc)
    ut = helpers.dt_to_ut(dt)
    assert ut == 0

    # time = one minute after when unix time starts
    dt = datetime.datetime(1970, 1, 1, 0, 1, 0, 0, tzinfo=timezone.utc)
    ut = helpers.dt_to_ut(dt)
    assert ut == 60


@enforce_types
def test_ut_to_dt_main():
    # time = when unix time starts
    ut = 0
    target_dt = datetime.datetime(1970, 1, 1, 0, 0, 0, 0, tzinfo=timezone.utc)

    dt = helpers.ut_to_dt(ut)
    assert dt.tzinfo == timezone.utc, "must be in UTC"
    assert dt == target_dt

    # time = one minute after when unix time starts
    ut = 60
    target_dt = datetime.datetime(1970, 1, 1, 0, 1, 0, 0, tzinfo=timezone.utc)

    dt = helpers.ut_to_dt(ut)
    assert dt.tzinfo == timezone.utc, "must be in UTC"
    assert dt == target_dt

@enforce_types
def test_calc_nmse():
    # values taken from Predict-ETH round 7, see https://rb.gy/2bzw9
    cex_vals = [1910.55, 1908.81, 1910.34, 1912.62, 1912.3, 1906.73, 1907.19, 1906.07, 1903.51, 1905.29, 1904.49, 1904.94]

    # rank1 is first place, rank2 is second-place, rank3 third-place.
    # rank83 is 83rd place, the lowest-ranked for nmses < 1.0 (in round 7)
    
    # rank1 is NFT #232/252. From 0xa98e504040b68e6a281fd489fcd1658df9703a91
    # - old nmse measure = 1.154e-06
    rank1_vals = [1909.8423071678906, 1909.3890122067048, 1909.0222544696958, 1908.606595942218, 1908.221036039253, 1907.8194953230318, 1907.4288513924025, 1907.0334268573008, 1906.6423661565814, 1906.250335445668, 1905.8604458939187, 1905.4708827925176]
    rank1_nmse_target = 1.154e-06

    # rank2 is NFT #108/252. From 0xca27c95f0eea6a0645dd7dddac46dfa893099fd6
    # - old nmse measure = 2.062e-06
    rank2_vals = [1911.36499651, 1911.45471804, 1907.85007032, 1907.76035838, 1908.34218631, 1908.09114526, 1907.87335393, 1907.54652541, 1907.35899274, 1907.67254935, 1907.21127253, 1907.06131286]
    rank2_nmse_target = 2.062e-06

    # rank3 is NFT #237/252. From 0x9cb9a72299f715cbd58bcdf8b7fdc1107631114e
    # - old nmse measure = 2.463e-06
    rank3_vals = [1910.3733053054548, 1910.082665202505, 1910.0324737706073, 1909.7306240431174, 1909.687171551225, 1909.38118747041, 1909.337257891959, 1909.0343962949887, 1908.9827923561074, 1908.6900915386434, 1908.624031004779, 1908.3479237283066]
    rank3_nmse_target = 2.463e-06

    # rank83 is NFT #106/252. From 0xd9b371ad6d6ee59315b7c1bb891fc4e85fbeaae5
    # - old nmse measure = 6.856e-03
    rank83_vals = [2065.89, 2065.62, 2065.62, 2065.62, 2063.42, 2068.25, 2065.89, 2068.36, 2065.89, 2065.89, 2063.82, 2063.72]
    rank83_nmse_target = 6.856e-03
