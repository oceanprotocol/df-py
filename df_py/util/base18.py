from enforce_typing import enforce_types


@enforce_types
def from_wei(amt_base: int, decimals: int = 18) -> float:
    return float(amt_base / (10 ** decimals))


@enforce_types
def to_wei(amt_eth, decimals: int = 18) -> int:
    return int(amt_eth * (10 ** decimals))


@enforce_types
def str_with_wei(amt_wei: int, decimals: int = 18) -> str:
    return f"{from_wei(amt_wei, decimals)} ({amt_wei} wei)"
