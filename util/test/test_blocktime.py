import brownie
from pytest import approx
from util.blocktime import timestrToBlock, timestrToTimestamp, timestampToBlock

chain = brownie.network.chain


def test_timestrToBlock_1():
    # tests here are light, the real tests are in test_*() below
    assert timestrToBlock(chain, "2022-03-29") >= 0.0
    assert timestrToBlock(chain, "2022-03-29_0:00") >= 0.0


def test_timestampToBlock_FarLeft():
    b = timestrToBlock(chain, "1970-01-01")
    assert b == 0 and isinstance(b, int)

    b = timestrToBlock(chain, "1970-01-01_0:00")
    assert b == 0 and isinstance(b, int)


def test_timestampToBlock_FarRight():
    b = timestrToBlock(chain, "2030-01-01")
    assert b == len(chain) and isinstance(b, int)

    b = timestrToBlock(chain, "2030-01-01_0:00")
    assert b == len(chain) and isinstance(b, int)


def test_timestrToTimestamp():
    t = timestrToTimestamp("1970-01-01_0:00")
    assert t == 0.0 and isinstance(t, float)

    t = timestrToTimestamp("2022-03-29_17:55")
    assert t == 1648576500.0 and isinstance(t, float)

    t = timestrToTimestamp("2022-03-29")
    assert t == 1648512000.0 and isinstance(t, float)


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
