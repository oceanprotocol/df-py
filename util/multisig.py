import os
import json
import requests
import brownie
from brownie import web3

# from web3 import Web3
from util import networkutil


def get_safe_nonce(multisig_address):
    BASE_URL = networkutil.chainIdToMultisigUri(brownie.network.chain.id)
    API_QUERY = "?limit=1&executed=false&queued=true&trusted=true"
    API_URL = f"{BASE_URL}/api/v1/safes/{multisig_address}/all-transactions/{API_QUERY}"
    response = requests.request("GET", API_URL)
    data = response.json()
    return data["results"][0]["nonce"] + 1


def send_multisig_tx(multisig_address, to, value, data):
    nonce = get_safe_nonce(multisig_address)
    BASE_URL = networkutil.chainIdToMultisigUri(brownie.network.chain.id)
    API_URL = f"{BASE_URL}/api/v1/safes/{multisig_address}/multisig-transactions/"
    safe_hash = "0x714aaa0313d34ffdf8c794b69c3edc4e2f45e166ef3ef1ee0be2d32e638e2241"
    # sign transaction hash
    PK = os.getenv("DFTOOL_KEY")
    acc = web3.eth.account.from_key(PK)
    sender_address = acc.address
    sig = acc.signHash(safe_hash)
    sig_hex = sig.signature.hex()
    gas = 0  # web3.eth.estimateGas(tx_dict)
    gasPrice = 0
    # proxy contract
    # contract = B.interface.IGnosisSafe(multisig_address_real)
    # hash = contract.getTransactionHash(
    #     to,
    #     value,
    #     data,
    #     0,
    #     gas,
    #     gas,
    #     gasPrice,
    #     "0x0000000000000000000000000000000000000000",
    #     "0x0000000000000000000000000000000000000000",
    #     nonce,
    # )
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

    response = requests.request("POST", API_URL, headers=headers, data=json_payload)
    print(response.text.encode("utf8"))

    # Fix this later
    safe_hash = response.text.split("=")[1]
    safe_hash = safe_hash.split(" ")[0]
    sig = acc.signHash(safe_hash)

    payload["contractTransactionHash"] = safe_hash
    payload["signature"] = sig.signature.hex()
    json_payload = json.dumps(payload)
    response = requests.request("POST", API_URL, headers=headers, data=json_payload)
    print(response.text.encode("utf8"))
    print(acc.address)
