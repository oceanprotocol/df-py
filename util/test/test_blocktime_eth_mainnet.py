from datetime import datetime
import os
import types
import brownie

from pytest import approx
from enforce_typing import enforce_types

from util import networkutil
from util.blocktime import (
    ethFindClosestBlock,
    ethTimestamptoBlock,
    timestrToBlock,
)

PREV = None
chain = None


@enforce_types
def test_ethTimestamptoBlock():
    ts = chain[-5000].timestamp
    block = chain[-5000].number

    guess = ethTimestamptoBlock(chain, ts)

    assert guess == approx(block, 10)


def test_timestrToBlock_eth_1():
    ts = chain[-5000].timestamp
    block = chain[-5000].number

    # convert ts to YYYY-MM-DD_HH:MM
    dt = datetime.fromtimestamp(ts)
    dt_str = dt.strftime("%Y-%m-%d_%H:%M:%S")

    guess = timestrToBlock(chain, dt_str, True)

    assert guess == block


@enforce_types
def test_timestrToBlock_eth_2():
    expected = 15735470
    ts = 1665619200
    dt = datetime.fromtimestamp(ts)
    dt_str = dt.strftime("%Y-%m-%d_%H:%M:%S")

    guess = timestrToBlock(chain, dt_str, True)
    assert guess == expected


@enforce_types
def test_timestrToBlock_eth_3():
    expected = 15835686
    dt_str = "2022-10-27"
    guess = timestrToBlock(chain, dt_str, True)
    assert guess == expected


@enforce_types
def test_ethFindClosestBlock():
    expected = 15835686

    # get timestamp last thu
    last_thu = 1666828800
    last_thu_block_guess = ethTimestamptoBlock(chain, last_thu)
    last_thu_block = ethFindClosestBlock(chain, last_thu_block_guess, last_thu)

    assert last_thu_block == expected


@enforce_types
def setup_function():
    global chain, PREV
    chain = brownie.network.chain

    PREV = types.SimpleNamespace()

    PREV.WEB3_INFURA_PROJECT_ID = os.environ.get("WEB3_INFURA_PROJECT_ID")

    # got this value from https://rpc.info/. We could also use our own
    os.environ["WEB3_INFURA_PROJECT_ID"] = "9aa3d95b3bc440fa88ea12eaa4456161"
    networkutil.connect(1)  # mainnet


@enforce_types
def teardown_function():
    networkutil.disconnect()

    global PREV

    if PREV.WEB3_INFURA_PROJECT_ID is None:
        del os.environ["WEB3_INFURA_PROJECT_ID"]
    else:
        os.environ["WEB3_INFURA_PROJECT_ID"] = PREV.WEB3_INFURA_PROJECT_ID
