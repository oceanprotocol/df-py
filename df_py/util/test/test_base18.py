#
# Copyright 2023 Ocean Protocol Foundation
# SPDX-License-Identifier: Apache-2.0
#

from df_py.util.base18 import from_wei, to_wei, str_with_wei


def test_wei():
    assert from_wei(int(1234 * 1e18)) == 1234
    assert from_wei(int(12.34 * 1e18)) == 12.34
    assert from_wei(int(0.1234 * 1e18)) == 0.1234

    assert to_wei(1234) == 1234 * 1e18 and type(to_wei(1234)) == int
    assert to_wei(12.34) == 12.34 * 1e18 and type(to_wei(12.34)) == int
    assert to_wei(0.1234) == 0.1234 * 1e18 and type(to_wei(0.1234)) == int

    assert str_with_wei(int(12.34 * 1e18)) == "12.34 (12340000000000000000 wei)"
