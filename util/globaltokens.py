import brownie
from enforce_typing import enforce_types

from util.constants import BROWNIE_PROJECT, GOD_ACCOUNT
from util.base18 import toBase18

_OCEAN_TOKEN = None


@enforce_types
def OCEANtoken(address=None):
    global _OCEAN_TOKEN  # pylint: disable=global-statement
    try:
        token = _OCEAN_TOKEN  # may trigger failure
        if token is not None:
            x = token.address  # "" # pylint: disable=unused-variable
    except brownie.exceptions.ContractNotFound:
        token = None
    if token is None:
        if address is None:
            token = _OCEAN_TOKEN = BROWNIE_PROJECT.Simpletoken.deploy(
                "OCEAN", "OCEAN", 18, toBase18(1e9), {"from": GOD_ACCOUNT}
            )
        else:
            token = BROWNIE_PROJECT.Simpletoken.at(address)
    return token


@enforce_types
def OCEAN_address() -> str:
    return OCEANtoken().address


@enforce_types
def fundOCEANFromAbove(dst_address: str, amount_base: int):
    OCEANtoken().transfer(dst_address, amount_base, {"from": GOD_ACCOUNT})
