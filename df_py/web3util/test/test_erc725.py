from enforce_typing import enforce_types
from web3 import Web3

from df_py.web3util.erc725 import (
    info_from_725,
    key_to_725,
    value_from_725,
    info_from_725,
    value_to_725,
)


@enforce_types
def test_key():
    key = "name"
    key725 = key_to_725(key)
    assert key725 == Web3.keccak(key.encode("utf-8")).hex()


@enforce_types
def test_value():
    value = "ETH/USDT"
    value725 = value_to_725(value)
    value_again = value_from_725(value725)

    assert value == value_again
    assert value == Web3.to_text(hexstr=value725)


@enforce_types
def test_info_from_725():
    info725_list = [
        {"key": key_to_725("pair"), "value": value_to_725("ETH/USDT")},
        {"key": key_to_725("timeframe"), "value": value_to_725("5m")},
    ]
    info_dict = info_from_725(info725_list)
    assert info_dict == {
        "pair": "ETH/USDT",
        "timeframe": "5m",
        "base": None,
        "quote": None,
        "source": None,
    }
