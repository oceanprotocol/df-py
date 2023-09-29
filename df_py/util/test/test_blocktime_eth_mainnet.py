import os
import types
from datetime import datetime

from enforce_typing import enforce_types
from pytest import approx

from df_py.util import networkutil
from df_py.util.blocktime import (
    eth_find_closest_block,
    eth_timestamp_to_block,
    timestr_to_block,
)
from df_py.util.oceanutil import get_rpc_url, get_web3


@enforce_types
def test_eth_timestamp_to_block(monkeypatch):
    monkeypatch.setenv("WEB3_INFURA_PROJECT_ID", "9aa3d95b3bc440fa88ea12eaa4456161")
    monkeypatch.setenv("MAINNET_RPC_URL", "https://mainnet.infura.io/v3/")
    web3 = get_web3(get_rpc_url("mainnet"))
    current_block = web3.eth.get_block("latest").number
    blocks_ago = web3.eth.get_block(current_block - 5000)

    ts = blocks_ago.timestamp
    block = blocks_ago.number

    guess = eth_timestamp_to_block(web3, ts)

    assert guess == approx(block, 10)


def test_timestr_to_block_eth_1(monkeypatch):
    monkeypatch.setenv("WEB3_INFURA_PROJECT_ID", "9aa3d95b3bc440fa88ea12eaa4456161")
    monkeypatch.setenv("MAINNET_RPC_URL", "https://mainnet.infura.io/v3/")
    web3 = get_web3(get_rpc_url("mainnet"))
    current_block = web3.eth.get_block("latest").number
    blocks_ago = web3.eth.get_block(current_block - 5000)

    ts = blocks_ago.timestamp
    block = blocks_ago.number

    # convert ts to YYYY-MM-DD_HH:MM
    dt = datetime.utcfromtimestamp(ts)
    dt_str = dt.strftime("%Y-%m-%d_%H:%M:%S")

    guess = timestr_to_block(web3, dt_str, True)

    assert guess == block


@enforce_types
def test_timestr_to_block_eth_2(monkeypatch):
    monkeypatch.setenv("WEB3_INFURA_PROJECT_ID", "9aa3d95b3bc440fa88ea12eaa4456161")
    monkeypatch.setenv("MAINNET_RPC_URL", "https://mainnet.infura.io/v3/")
    web3 = get_web3(get_rpc_url("mainnet"))

    expected = 15735470
    ts = 1665619200
    dt = datetime.utcfromtimestamp(ts)
    dt_str = dt.strftime("%Y-%m-%d_%H:%M:%S")

    guess = timestr_to_block(web3, dt_str, True)
    assert guess == expected


@enforce_types
def test_timestr_to_block_eth_3(monkeypatch):
    monkeypatch.setenv("WEB3_INFURA_PROJECT_ID", "9aa3d95b3bc440fa88ea12eaa4456161")
    monkeypatch.setenv("MAINNET_RPC_URL", "https://mainnet.infura.io/v3/")
    web3 = get_web3(get_rpc_url("mainnet"))

    expected = 15835686
    dt_str = "2022-10-27"
    guess = timestr_to_block(web3, dt_str, True)
    assert guess == expected


@enforce_types
def test_eth_find_closest_block(monkeypatch):
    monkeypatch.setenv("WEB3_INFURA_PROJECT_ID", "9aa3d95b3bc440fa88ea12eaa4456161")
    monkeypatch.setenv("MAINNET_RPC_URL", "https://mainnet.infura.io/v3/")
    web3 = get_web3(get_rpc_url("mainnet"))

    expected = 15835686

    # get timestamp last thu
    last_thu = 1666828800
    last_thu_block_guess = eth_timestamp_to_block(web3, last_thu)
    last_thu_block = eth_find_closest_block(web3, last_thu_block_guess, last_thu)

    assert last_thu_block == expected
