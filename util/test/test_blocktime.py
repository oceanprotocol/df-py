from datetime import datetime
from math import ceil
from pytest import approx

import brownie
from enforce_typing import enforce_types

from util import networkutil, oceanutil
from util.blocktime import (
    getBlockNumberThursday,
    getNextThursdayTimestamp,
    getstfinBlocks,
    timestrToBlock,
    timestrToTimestamp,
    timestampToBlock,
)

chain = None


@enforce_types
def test_timestrToBlock_1():
    # tests here are light, the real tests are in test_*() below
    assert timestrToBlock(chain, "2022-03-29") >= 0.0
    assert timestrToBlock(chain, "2022-03-29_0:00") >= 0.0


@enforce_types
def test_timestampToBlock_FarLeft():
    b = timestrToBlock(chain, "1970-01-01")
    assert b == 0 and isinstance(b, int)

    b = timestrToBlock(chain, "1970-01-01_0:00")
    assert b == 0 and isinstance(b, int)


@enforce_types
def test_timestampToBlock_FarRight():
    b = timestrToBlock(chain, "2030-01-01")
    assert b == len(chain) and isinstance(b, int)

    b = timestrToBlock(chain, "2030-01-01_0:00")
    assert b == len(chain) and isinstance(b, int)


@enforce_types
def test_timestrToTimestamp():
    t = timestrToTimestamp("1970-01-01_0:00")
    assert t == 0.0 and isinstance(t, float)

    t = timestrToTimestamp("2022-03-29_17:55")
    assert t == 1648576500.0 and isinstance(t, float)

    t = timestrToTimestamp("2022-03-29")
    assert t == 1648512000.0 and isinstance(t, float)


@enforce_types
def test_timestampToBlock():
    # gather timestamp and blocks at block offset 0, 9, 29
    timestamp0 = chain[-1].timestamp
    block0 = chain[-1].number

    chain.mine(blocks=1, timestamp=timestamp0 + 10.0)
    timestamp1 = chain[-1].timestamp
    block1 = chain[-1].number
    assert block1 == (block0 + 1)
    assert timestamp1 == (timestamp0 + 10.0)

    chain.mine(blocks=9, timestamp=timestamp1 + 90.0)
    timestamp9 = chain[-1].timestamp
    block9 = chain[-1].number
    assert block9 == (block1 + 9)
    assert timestamp9 == (timestamp1 + 90.0)

    chain.mine(blocks=20, timestamp=timestamp9 + 200.0)
    timestamp29 = chain[-1].timestamp
    block29 = chain[-1].number
    assert block29 == (block9 + 20)
    assert timestamp29 == (timestamp9 + 200.0)

    # test
    assert timestampToBlock(chain, timestamp0) == approx(block0, 1)
    assert timestampToBlock(chain, timestamp9) == approx(block9, 1)
    assert timestampToBlock(chain, timestamp29) == approx(block29, 1)

    assert timestampToBlock(chain, timestamp0 + 10.0) == approx(block0 + 1, 1)
    assert timestampToBlock(chain, timestamp0 + 20.0) == approx(block0 + 2, 1)

    assert timestampToBlock(chain, timestamp9 - 10.0) == approx(block9 - 1, 1)
    assert timestampToBlock(chain, timestamp9 + 10.0) == approx(block9 + 1, 1)

    assert timestampToBlock(chain, timestamp29 - 10.0) == approx(block29 - 1, 1)


@enforce_types
def test_get_next_thursday():
    next_thursday = getNextThursdayTimestamp()
    date = datetime.fromtimestamp(next_thursday)

    assert date.isoweekday() == 4


@enforce_types
def test_get_next_thursday_block_number():
    next_thursday_block = getBlockNumberThursday(chain)
    assert next_thursday_block % 10 == 0
    assert len(chain) < next_thursday_block

    now = len(chain) - 1

    t0 = chain[0].timestamp
    t1 = chain[int(now)].timestamp

    avgBlockTime = (t1 - t0) / now

    next_thursday = getNextThursdayTimestamp()
    apprx = (next_thursday - t0) / avgBlockTime
    apprx = ceil(apprx / 100) * 100

    assert next_thursday_block == approx(apprx, 1)


@enforce_types
def test_getstfinBlocks():
    chain.mine()
    # by block number
    (st, fin) = getstfinBlocks(chain, "0", "1")
    assert st == 0
    assert fin > 0

    # get by latest fin
    (st, fin) = getstfinBlocks(chain, "0", "latest")
    assert st == 0
    assert fin > 0

    # get by thu fin
    (st, fin) = getstfinBlocks(chain, "0", "thu")
    assert st == 0
    assert fin > 0

    # get by datetime YYYY-MM-DD
    now_date = datetime.fromtimestamp(chain[-1].timestamp)
    now_date = now_date.strftime("%Y-%m-%d")
    (st, fin) = getstfinBlocks(chain, "0", now_date)
    assert st == 0
    assert fin == 0


@enforce_types
def setup_function():
    networkutil.connect(networkutil.DEV_CHAINID)
    oceanutil.recordDevDeployedContracts()
    global chain
    chain = brownie.network.chain


@enforce_types
def teardown_function():
    networkutil.disconnect()
