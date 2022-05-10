from enforce_typing import enforce_types


@enforce_types
def toBase18(amt: float) -> int:
    return int(amt * 1e18)


@enforce_types
def fromBase18(amt_base: int) -> float:
    return amt_base / 1e18
