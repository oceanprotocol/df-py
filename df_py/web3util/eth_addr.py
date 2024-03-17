from enforce_typing import enforce_types


@enforce_types
def assert_is_eth_addr(s: str):
    # just a basic check
    assert s[:2] == "0x", s
