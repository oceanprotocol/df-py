#
# Copyright 2023 Ocean Protocol Foundation
# SPDX-License-Identifier: Apache-2.0
#
from ecies import decrypt as asymmetric_decrypt
from enforce_typing import enforce_types
from eth_utils import decode_hex


@enforce_types
def asym_decrypt(value_enc_h: str, privkey: str) -> str:
    """Asymmetrically decrypt a value, e.g. retrieved from get_data()"""
    value_enc_b = decode_hex(value_enc_h)  # bytes
    value_b = asymmetric_decrypt(privkey, value_enc_b)  # main work. bytes
    value = value_b.decode("ascii")
    return value
