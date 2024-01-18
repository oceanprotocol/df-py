import pytest

from datetime import datetime
from math import ceil
from unittest.mock import Mock

from enforce_typing import enforce_types
from pytest import approx

from df_py.util.blockrange import create_range
from df_py.util.blocktime import (
    get_block_number_thursday,
    get_next_thursday_timestamp,
    get_st_fin_blocks,
    timestamp_to_block,
    timestr_to_block,
    timestr_to_timestamp,
)


@enforce_types
def test_timestr_to_block_1(w3):
    # tests here are light, the real tests are in test_*() below
    assert timestr_to_block(w3, "2022-03-29") >= 0.0
    assert timestr_to_block(w3, "2022-03-29_0:00") >= 0.0


@enforce_types
def test_timestamp_to_block_far_left(w3):
    b = timestr_to_block(w3, "1970-01-01")
    assert b == 0 and isinstance(b, int)

    b = timestr_to_block(w3, "1970-01-01_0:00")
    assert b == 0 and isinstance(b, int)


@enforce_types
def test_timestamp_to_block_far_right(w3):
    b = timestr_to_block(w3, "2150-01-01")
    assert b == w3.eth.get_block("latest").number and isinstance(b, int)

    b = timestr_to_block(w3, "2150-01-01_0:00")
    assert b == w3.eth.get_block("latest").number and isinstance(b, int)


@enforce_types
def test_timestr_to_timestamp():
    t = timestr_to_timestamp("1970-01-01_0:00")
    assert t == 0.0 and isinstance(t, float)

    t = timestr_to_timestamp("2022-03-29_17:55")
    assert t == 1648576500.0 and isinstance(t, float)

    t = timestr_to_timestamp("2022-03-29")
    assert t == 1648512000.0 and isinstance(t, float)


@enforce_types
def test_timestamp_to_block(w3):
    # gather timestamp and blocks at block offset 0, 9, 29
    latest_block = w3.eth.get_block("latest")
    timestamp0 = latest_block.timestamp
    block0 = latest_block.number

    provider = w3.provider

    provider.make_request("evm_mine", [timestamp0 + 10])
    provider.make_request("evm_increaseTime", [10])
    latest_block = w3.eth.get_block("latest")
    timestamp1 = latest_block.timestamp
    block1 = latest_block.number
    assert block1 == (block0 + 1)
    assert timestamp1 == (timestamp0 + 10.0)

    for _ in range(9):
        provider.make_request("evm_mine", [])
        provider.make_request("evm_increaseTime", [10])

    latest_block = w3.eth.get_block("latest")
    timestamp9 = latest_block.timestamp
    block9 = latest_block.number
    assert block9 == (block1 + 9)
    assert timestamp9 == (timestamp1 + 90.0)

    for _ in range(20):
        provider.make_request("evm_mine", [])
        provider.make_request("evm_increaseTime", [10])

    latest_block = w3.eth.get_block("latest")
    timestamp29 = latest_block.timestamp
    block29 = latest_block.number
    assert block29 == (block9 + 20)
    assert timestamp29 == approx(timestamp9 + 200.0, 1)

    # test
    assert timestamp_to_block(w3, timestamp0) == approx(block0, 1)
    assert timestamp_to_block(w3, timestamp9) == approx(block9, 1)
    assert timestamp_to_block(w3, timestamp29) == approx(block29, 1)

    assert timestamp_to_block(w3, timestamp0 + 10.0) == approx(block0 + 1, 1)
    assert timestamp_to_block(w3, timestamp0 + 20.0) == approx(block0 + 2, 1)

    assert timestamp_to_block(w3, timestamp9 - 10.0) == approx(block9 - 1, 1)
    assert timestamp_to_block(w3, timestamp9 + 10.0) == approx(block9 + 1, 1)

    assert timestamp_to_block(w3, timestamp29 - 10.0) == approx(block29 - 1, 1)


@enforce_types
def test_timestamp_to_block_validation():
    target_ts = 10000
    web3 = Mock()
    web3.eth.get_block.return_value = 0

    with pytest.raises(Exception) as err:
        timestamp_to_block(web3, target_ts)

    assert (
        str(err.value)
        == "timestamp_to_block() is returning a block that is too far away"
    )


@enforce_types
def test_get_next_thursday(w3):
    next_thursday = get_next_thursday_timestamp(w3)
    date = datetime.utcfromtimestamp(next_thursday)

    assert date.isoweekday() == 4


@enforce_types
def test_get_next_thursday_block_number(w3):
    next_thursday_block = get_block_number_thursday(w3)
    assert next_thursday_block % 10 == 0
    assert w3.eth.get_block("latest").number < next_thursday_block

    now = w3.eth.get_block("latest").number - 1

    t0 = w3.eth.get_block(0).timestamp
    t1 = w3.eth.get_block(int(now)).timestamp

    avgBlockTime = (t1 - t0) / now

    next_thursday = get_next_thursday_timestamp(w3)
    apprx = (next_thursday - t0) / avgBlockTime
    apprx = ceil(apprx / 100) * 100

    assert next_thursday_block == approx(apprx, 1)


@enforce_types
def test_get_st_fin_blocks(w3):
    provider = w3.provider
    provider.make_request("evm_mine", [])

    # by block number
    (st, fin) = get_st_fin_blocks(w3, "0", "1")
    assert st == 0
    assert fin > 0

    # get by latest fin
    (st, fin) = get_st_fin_blocks(w3, "0", "latest")
    assert st == 0
    assert fin > 0

    # get by thu fin
    (st, fin) = get_st_fin_blocks(w3, "0", "thu")
    assert st == 0
    assert fin > 0

    # get by datetime YYYY-MM-DD
    now_date = datetime.utcfromtimestamp(w3.eth.get_block("latest").timestamp)
    now_date = now_date.strftime("%Y-%m-%d")
    (st, fin) = get_st_fin_blocks(w3, "0", now_date)
    assert st == 0
    assert fin >= 0

    # test in conjunction with create_range in blockrange
    # to avoid extra setup in test_blockrange.py just for one test
    rng = create_range(w3, 10, 5000, 100, 42)
    assert rng
