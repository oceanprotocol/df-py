#
# Copyright 2023 Ocean Protocol Foundation
# SPDX-License-Identifier: Apache-2.0
#

from df_py.util.base18 import from_wei, str_with_wei, to_wei


def test_wei():
    assert from_wei(int(1234 * 1e18)) == 1234
    assert from_wei(int(12.34 * 1e18)) == 12.34
    assert from_wei(int(0.1234 * 1e18)) == 0.1234

    assert to_wei(1234) == 1234 * 1e18 and type(to_wei(1234)) == int
    assert to_wei(12.34) == 12.34 * 1e18 and type(to_wei(12.34)) == int
    assert to_wei(0.1234) == 0.1234 * 1e18 and type(to_wei(0.1234)) == int

    assert str_with_wei(int(12.34 * 1e18)) == "12.34 (12340000000000000000 wei)"


def test_wei_with_custom_decimals():
    # Test with 9 decimals (USDC)
    assert from_wei(int(1234 * 1e9), decimals=9) == 1234
    assert from_wei(int(12.34 * 1e9), decimals=9) == 12.34
    assert from_wei(int(0.1234 * 1e9), decimals=9) == 0.1234

    assert to_wei(1234, decimals=9) == 1234 * 1e9 and type(to_wei(1234, decimals=9)) == int
    assert to_wei(12.34, decimals=9) == 12.34 * 1e9 and type(to_wei(12.34, decimals=9)) == int
    assert to_wei(0.1234, decimals=9) == 0.1234 * 1e9 and type(to_wei(0.1234, decimals=9)) == int

    assert str_with_wei(int(12.34 * 1e9), decimals=9) == "12.34 (12340000000 wei)"

    # Test with 6 decimals (USDT)
    assert from_wei(int(100 * 1e6), decimals=6) == 100
    assert to_wei(100, decimals=6) == 100 * 1e6 and type(to_wei(100, decimals=6)) == int

    # Test with 8 decimals (WBTC)
    assert from_wei(int(50 * 1e8), decimals=8) == 50
    assert to_wei(50, decimals=8) == 50 * 1e8 and type(to_wei(50, decimals=8)) == int
