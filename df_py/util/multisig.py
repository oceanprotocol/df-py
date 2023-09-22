import json
import os

import requests

# from web3 import Web3
from df_py.util import networkutil


def get_safe_nonce(multisig_address):
    BASE_URL = networkutil.chain_id_to_multisig_uri(brownie.network.chain.id)
    API_QUERY = "?limit=10&executed=false&queued=true&trusted=true"
    API_URL = f"{BASE_URL}/api/v1/safes/{multisig_address}/all-transactions/{API_QUERY}"
    response = requests.request("GET", API_URL, timeout=30)
    data = response.json()
    nonce = None
    for d in data["results"]:
        if "nonce" in d:
            nonce = d["nonce"]
            break
    if nonce is None:
        # pylint: disable=broad-exception-raised
        raise Exception("Couldn't get multisig nonce")
    return nonce + 1


def send_multisig_tx(multisig_address, to, value, data):
    nonce = get_safe_nonce(multisig_address)
    BASE_URL = networkutil.chain_id_to_multisig_uri(brownie.network.chain.id)
    API_URL = f"{BASE_URL}/api/v1/safes/{multisig_address}/multisig-transactions/"
    contract = ContractBase(web3, "interfaces/IGnosisSafe", multisig_address)
    gas = 0
    gasPrice = 0
    safe_hash = contract.getTransactionHash(
        to,
        value,
        data,
        0,
        gas,
        gas,
        gasPrice,
        "0x0000000000000000000000000000000000000000",
        "0x0000000000000000000000000000000000000000",
        nonce,
    ).hex()
    # sign transaction hash
    PK = os.getenv("DFTOOL_KEY")
    acc = web3.eth.account.from_key(PK)
    sender_address = acc.address
    sig = acc.signHash(safe_hash)
    sig_hex = sig.signature.hex()
    # proxy contract
    payload = {
        "value": value,
        "safeTxGas": gas,
        "baseGas": gas,
        "gasPrice": gasPrice,
        "nonce": nonce,
        "operation": 0,
        "from": multisig_address,
        "to": to,
        "sender": sender_address,
        "signature": sig_hex,
        "data": data,
        "contractTransactionHash": safe_hash,
        "gasToken": "0x0000000000000000000000000000000000000000",
        "refundReceiver": "0x0000000000000000000000000000000000000000",
    }
    json_payload = json.dumps(payload)
    headers = {"Content-Type": "application/json"}

    response = requests.request(
        "POST", API_URL, headers=headers, data=json_payload, timeout=30
    )
    print(response.text.encode("utf8"))
