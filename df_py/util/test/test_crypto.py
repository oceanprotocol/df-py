from enforce_typing import enforce_types

from df_py.util import crypto


@enforce_types
def test_asym_encrypt_decrypt(w3):
    alice = w3.eth.account.create()

    privkey = alice._private_key.hex()  # str
    pubkey = crypto.calc_pubkey(privkey)  # str

    value = "hello there"
    value_enc = crypto.asym_encrypt(value, pubkey)
    assert value_enc != value

    value2 = crypto.asym_decrypt(value_enc, privkey)
    assert value2 == value
