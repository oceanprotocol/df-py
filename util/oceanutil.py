from collections import namedtuple
import hashlib
import json
from typing import Any, Dict, List, Tuple

import brownie
from enforce_typing import enforce_types

from util.constants import ZERO_ADDRESS


# =============================================================================
# fee stuff needed for consume

# follow order in ocean.py/ocean_lib/structures/abi_tuples.py::ConsumeFees
@enforce_types
def get_zero_consume_mkt_fee_tuple() -> Tuple:
    d = {
        "consumeMarketFeeAddress": ZERO_ADDRESS,
        "consumeMarketFeeToken": ZERO_ADDRESS,
        "consumeMarketFeeAmount": 0,
    }

    consume_mkt_fee = (
        d["consumeMarketFeeAddress"],
        d["consumeMarketFeeToken"],
        d["consumeMarketFeeAmount"],
    )
    return consume_mkt_fee


# follow order in ocean.py/ocean_lib/structures/abi_tuples.py::ProviderFees
@enforce_types
def get_zero_provider_fee_tuple(pub_account) -> Tuple:
    d = get_zero_provider_fee_dict(pub_account)

    provider_fee = (
        d["providerFeeAddress"],
        d["providerFeeToken"],
        d["providerFeeAmount"],
        d["v"],
        d["r"],
        d["s"],
        d["validUntil"],
        d["providerData"],
    )

    return provider_fee


# from ocean.py/tests/resources/helper_functions.py
@enforce_types
def get_zero_provider_fee_dict(provider_account) -> Dict[str, Any]:
    web3 = brownie.web3
    provider_fee_amount = 0
    compute_env = None
    provider_data = json.dumps({"environment": compute_env}, separators=(",", ":"))
    provider_fee_address = provider_account.address
    provider_fee_token = ZERO_ADDRESS
    valid_until = 0

    message = web3.solidityKeccak(
        ["bytes", "address", "address", "uint256", "uint256"],
        [
            web3.toHex(web3.toBytes(text=provider_data)),
            provider_fee_address,
            provider_fee_token,
            provider_fee_amount,
            valid_until,
        ],
    )
    signed = web3.eth.sign(provider_fee_address, data=message)
    signature = split_signature(signed)

    provider_fee = {
        "providerFeeAddress": provider_fee_address,
        "providerFeeToken": provider_fee_token,
        "providerFeeAmount": provider_fee_amount,
        "providerData": web3.toHex(web3.toBytes(text=provider_data)),
        # make it compatible with last openzepellin
        # https://github.com/OpenZeppelin/openzeppelin-contracts/pull/1622
        "v": signature.v,
        "r": signature.r,
        "s": signature.s,
        "validUntil": 0,
    }

    return provider_fee


# from ocean.py/ocean_lib/web3_internal/utils.py
Signature = namedtuple("Signature", ("v", "r", "s"))

# from ocean.py/ocean_lib/web3_internal/utils.py
@enforce_types
def split_signature(signature: Any) -> Signature:
    """
    :param signature: signed message hash, hex str
    """
    web3 = brownie.web3
    assert len(signature) == 65, (
        f"invalid signature, " f"expecting bytes of length 65, got {len(signature)}"
    )
    v = web3.toInt(signature[-1])
    r = to_32byte_hex(int.from_bytes(signature[:32], "big"))
    s = to_32byte_hex(int.from_bytes(signature[32:64], "big"))
    if v != 27 and v != 28:
        v = 27 + v % 2

    return Signature(v, r, s)


# from ocean.py/ocean_lib/web3_internal/utils.py
@enforce_types
def to_32byte_hex(val: int) -> str:
    """

    :param val:
    :return:
    """
    web3 = brownie.web3
    return web3.toHex(web3.toBytes(val).rjust(32, b"\0"))


@enforce_types
def calcDID(nft_addr: str, chainID: int) -> str:
    nft_addr2 = brownie.web3.toChecksumAddress(nft_addr)

    # adapted from ocean.py/ocean_lib/ocean/ocean_assets.py
    did = f"did:op:{create_checksum(nft_addr2 + str(chainID))}"
    return did


# from ocean.py/ocean_lib/utils/utilities.py
@enforce_types
def create_checksum(text: str) -> str:
    """
    :return: str
    """
    return hashlib.sha256(text.encode("utf-8")).hexdigest()
