from enforce_typing import enforce_types
from typing import Union

@enforce_types
def toBase18(amt: Union[float, int]) -> int:
    return int(amt * 1e18)


@enforce_types
def fromBase18(amt_base: int) -> float:
    return amt_base / 1e18
