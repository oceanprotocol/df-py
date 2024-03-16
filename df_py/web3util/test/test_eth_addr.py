from enforce_typing import enforce_types
import pytest

from df_py.web3util.eth_addr import assert_is_eth_addr

@enforce_types
def test_eth_addr():
    for good in [
            "0x",
            "0x123",
            "0xadafs",
    ]:
        assert_is_eth_addr(good)

    for bad in [
            "",
            "123",
            "adfsfs",
            ]
    with pytest.raises(AssertionError):
        assert_is_eth_addr(bad)

    with pytest.raises(TypeError):
        assert_is_eth_addr(34)
    
