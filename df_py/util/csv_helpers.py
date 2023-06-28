import re

from enforce_typing import enforce_types


@enforce_types
def assert_is_eth_addr(s: str):
    # just a basic check
    assert s[:2] == "0x", s


@enforce_types
def _last_int(s: str) -> int:
    """Return the last integer in the given str"""
    nbr_strs = re.findall("[0-9]+", s)
    return int(nbr_strs[-1])
