from datetime import datetime, timezone
from typing import Union

import numpy as np
from enforce_typing import enforce_types


@enforce_types
def dt_to_ut(dt: datetime) -> int:
    """datetime to unixtime"""
    assert dt.tzinfo == timezone.utc, "must be in UTC"
    ut = int(dt.timestamp())
    return ut


@enforce_types
def ut_to_dt(ut: Union[int, float]) -> datetime:
    """unixtime to datetime"""
    dt = datetime.utcfromtimestamp(ut)
    dt = dt.replace(tzinfo=timezone.utc)
    assert dt.tzinfo == timezone.utc, "must be in UTC"
    return dt


@enforce_types
def pretty_time(dt: datetime) -> str:
    return dt.strftime("%Y/%m/%d, %H:%M:%S")


@enforce_types
def print_datetime_info(descr: str, uts: list):
    dts = [ut_to_dt(ut) for ut in uts]
    print(descr + ":")
    print(f"  starts on: {pretty_time(dts[0])}")
    print(f"    ends on: {pretty_time(dts[-1])}")
    print(f"  {len(dts)} datapoints")
    print(f"  time interval between datapoints: {(dts[1]-dts[0])}")


@enforce_types
def filter_to_target_uts(
    target_uts: list, unfiltered_uts: list, unfiltered_vals: list
) -> list:
    """Return filtered_vals -- values at at the target timestamps"""
    filtered_vals = [None] * len(target_uts)
    for i, target_ut in enumerate(target_uts):
        time_diffs = np.abs(np.asarray(unfiltered_uts) - target_ut)
        tol_s = 1  # should always align within e.g. 1 second
        target_dt = ut_to_dt(target_ut)
        target_ut_s = pretty_time(target_dt)
        assert (
            min(time_diffs) <= tol_s
        ), f"Unfiltered times is missing target time: {target_ut_s}"
        j = np.argmin(time_diffs)
        filtered_vals[i] = unfiltered_vals[j]
    return filtered_vals


@enforce_types
def calc_nmse(y, yhat) -> float:
    assert len(y) == len(yhat)
    mse_xy = np.sum(np.square(np.asarray(y) - np.asarray(yhat)))
    mse_x = np.sum(np.square(np.asarray(y)))
    nmse = mse_xy / mse_x
    return nmse
