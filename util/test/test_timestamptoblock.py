import os
import types
import brownie

from pytest import approx
from enforce_typing import enforce_types

from util import networkutil
from util.blocktime import (
    ethFindFirstThuBlock,
    ethTimestamptoBlock,
)

PREV = None
chain = None


@enforce_types
def test_ethTimestamptoBlock():
    _chain = brownie.network.chain
    ts = _chain[-5000].timestamp
    block = _chain[-5000].number

    guess = ethTimestamptoBlock(_chain, ts)

    assert guess == approx(block, 10)


@enforce_types
def test_ethFindFirstThuBlock():
    _chain = brownie.network.chain

    expected = 15835687

    # get timestamp last thu
    last_thu = 1666828800
    last_thu_block_guess = ethTimestamptoBlock(_chain, last_thu)
    last_thu_block = ethFindFirstThuBlock(_chain, last_thu_block_guess)

    assert last_thu_block == expected


@enforce_types
def setup_function():
    networkutil.connect(1)  # mainnet
    global chain
    chain = brownie.network.chain

    global PREV

    PREV = types.SimpleNamespace()

    PREV.WEB3_INFURA_PROJECT_ID = os.environ.get("WEB3_INFURA_PROJECT_ID")

    # got this value from https://rpc.info/. We could also use our own
    os.environ["WEB3_INFURA_PROJECT_ID"] = "9aa3d95b3bc440fa88ea12eaa4456161"


@enforce_types
def teardown_function():
    networkutil.disconnect()

    global PREV

    if PREV.WEB3_INFURA_PROJECT_ID is None:
        del os.environ["WEB3_INFURA_PROJECT_ID"]
    else:
        os.environ["WEB3_INFURA_PROJECT_ID"] = PREV.WEB3_INFURA_PROJECT_ID
