from enforce_typing import enforce_types


@enforce_types
def from_wei(amt_base: int) -> float:
    return float(amt_base / 1e18)


@enforce_types
def to_wei(amt_eth) -> int:
    return int(amt_eth * 1e18)


@enforce_types
def str_with_wei(amt_wei: int) -> str:
    return f"{from_wei(amt_wei)} ({amt_wei} wei)"
