from enforce_typing import enforce_types
from eth_account.account import Account

from df_py.mathutil.crypto import (
    calc_pubkey,
    asym_encrypt,
    asym_decrypt,
)


@enforce_types
def test_asym_encrypt_decrypt():
    alice = Account.create()  # pylint: disable=no-value-for-parameter

    privkey = alice._private_key.hex()  # str
    pubkey = calc_pubkey(privkey)  # str

    value = "hello there"
    value_enc = asym_encrypt(value, pubkey)
    assert value_enc != value

    value2 = asym_decrypt(value_enc, privkey)
    assert value2 == value
