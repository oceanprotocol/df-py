#
# Copyright 2023 Ocean Protocol Foundation
# SPDX-License-Identifier: Apache-2.0
#
from ecies import decrypt as asymmetric_decrypt
from ecies import encrypt as asymmetric_encrypt
from enforce_typing import enforce_types
from eth_keys import keys
from eth_utils import decode_hex


@enforce_types
def calc_pubkey(privkey: str) -> str:
    privkey_obj = keys.PrivateKey(decode_hex(privkey))
    pubkey = str(privkey_obj.public_key)  # str
    return pubkey


@enforce_types
def asym_encrypt(value: str, pubkey: str) -> str:
    """Asymmetrically encrypt a value, e.g. ready to store in set_data()"""
    value_b = value.encode("utf-8")  # binary
    value_enc_b = asymmetric_encrypt(pubkey, value_b)  # main work. binary
    value_enc_h = value_enc_b.hex()  # hex str
    return value_enc_h


@enforce_types
def asym_decrypt(value_enc_h: str, privkey: str) -> str:
    """Asymmetrically decrypt a value, e.g. retrieved from get_data()"""
    value_enc_b = decode_hex(value_enc_h)  # bytes
    value_b = asymmetric_decrypt(privkey, value_enc_b)  # main work. bytes
    value = value_b.decode("ascii")
    return value
