import os
import sys
from datetime import datetime as dt
from datetime import timedelta
from typing import List

import ccxt
import requests
from enforce_typing import enforce_types
from ocean_lib.models.data_nft import DataNFT
from ocean_lib.ocean import crypto
from predict_eth.helpers import (
    calc_nmse,
    create_alice_wallet,
    create_ocean_instance,
    filter_to_target_uts,
    print_datetime_info,
    target_12h_unixtimes,
)

# Set network. Change this one line if needed. *Supposed* to be "polygon-test"
NETWORK_NAME = "polygon-test"  # polygon-test (Mumbai), polygon-main, goerli...

# Auto-calc chainid
NAME_TO_CHAINID = {"polygon-test": 80001, "polygon-main": 137, "goerli": 5}
CHAINID = NAME_TO_CHAINID[NETWORK_NAME]

# Usage instructions
HELP_JUDGE = f"""predict-eth-judge

Usage: dftool judge DEADLINE

DEADLINE expected in the format YEAR-MONTH-DAY_HOUR:MIN in UTC.
   Eg 2023-04-06_1:00
DEADLINE refers to the end of the challenge itself, to limit entry retrieval.

Hard-coded values: NETWORK_NAME={NETWORK_NAME}, CHAINID={CHAINID}
Ennvars expected:
   REMOTE_TEST_PRIVATE_KEY1 (for judges' account)
   POLYGONSCAN_API_KEY

"""


@enforce_types
def get_nft_addresses(deadline_dt):
    a_week_before_deadline = deadline_dt - timedelta(weeks=1)
    url = "https://api-testnet.polygonscan.com/api"
    params = {
        "module": "account",
        "action": "tokennfttx",
        "address": "0xA54ABd42b11B7C97538CAD7C6A2820419ddF703E",
        "apikey": os.getenv("POLYGONSCAN_API_KEY"),
    }
    txs = requests.get(url, params=params).json()["result"]

    for tx in txs:
        tx["timeStamp"] = dt.utcfromtimestamp(int(tx["timeStamp"]))

    # each tx is a dict that includes:
    # {'timeStamp': '1677562009',
    # 'hash': '0x163991c9fb2c94b7452909a1bd8cf4d298d92dc90ef2e49ab13dc935f0552061',
    # 'from': '0x04815de815db15a3086425b58981545bec018a6a',
    # 'contractAddress': '0x458420a012cb7e63ae24ecf83eb21ab7c40d71d8',
    # 'to': '0xa54abd42b11b7c97538cad7c6a2820419ddf703e',
    # 'tokenID': '1', 'tokenName': 'Data NFT 1', 'tokenSymbol': 'DN1'}

    filtered_txs = [
        tx for tx in txs if a_week_before_deadline < tx["timeStamp"] <= deadline_dt
    ]

    return [tx["contractAddress"] for tx in filtered_txs]


@enforce_types
def nft_addr_to_pred_vals(nft_addr: str, ocean, alice) -> List[float]:
    # adapted from "What judges will do" in
    #  https://github.com/oceanprotocol/predict-eth/blob/main/challenges/main4.md

    # get predicted ETH values
    nft = DataNFT(ocean.config_dict, nft_addr)
    pred_vals_str_enc = nft.get_data("predictions")
    try:
        pred_vals_str = crypto.asym_decrypt(pred_vals_str_enc, alice.private_key)
        pred_vals = [float(s) for s in pred_vals_str[1:-1].split(",")]
    except:  # pylint: disable=W0702
        return []

    return pred_vals


def get_cex_vals(deadline_dt):
    target_uts = target_12h_unixtimes(deadline_dt + timedelta(minutes=1))
    print_datetime_info("target times", target_uts)

    # get actual ETH values
    cex_x = ccxt.kraken().fetch_ohlcv("ETH/USDT", "5m")
    allcex_uts = [xi[0] / 1000 for xi in cex_x]
    allcex_vals = [xi[4] for xi in cex_x]
    # print_datetime_info("CEX data info", allcex_uts)
    cex_vals = filter_to_target_uts(target_uts, allcex_uts, allcex_vals)
    print(f"cex ETH price is ${cex_vals[0]} at target time 0")
    print(f"cex_vals: {cex_vals}")

    return cex_vals


def parse_arguments(arguments):
    if len(arguments) != 3 or arguments[1] != "judge":
        print(HELP_JUDGE)
        sys.exit(0)

    # extract inputs
    deadline_dt = dt.strptime(arguments[2], "%Y-%m-%d_%H:%M")

    print("judging: Begin")
    deadline_dt_str = deadline_dt.strftime("%Y-%m-%d_%H:%M")
    print(f"Args: DEADLINE={deadline_dt_str}")

    return deadline_dt


def print_address_nmse(nmses):
    for address, nmse in nmses.items():
        print(f"Address: {address}, NMSE: {nmse}")


def print_nmses_results(nmses):
    print("\n-------------")
    print("Summary:")
    print("-------------")

    print(f"\n{len(nmses)} entries:")
    print_address_nmse(nmses)

    ranking = dict(sorted(nmses.items(), key=lambda item: item[1]))
    print("\nafter ranking:")
    print("-------------")
    print_address_nmse(ranking)

    print("\ntop 3:")
    print("-------------")
    print("\n".join(list(ranking.keys())[:3]))

    print("\njudge: Done")


@enforce_types
def do_get_nmses(arguments):
    ocean = create_ocean_instance(NETWORK_NAME)
    alice_private_key = os.getenv("REMOTE_TEST_PRIVATE_KEY1")
    assert alice_private_key, "need envvar REMOTE_TEST_PRIVATE_KEY1"
    alice = create_alice_wallet(ocean)  # uses REMOTE_TEST_PRIVATE_KEY1

    deadline_dt = parse_arguments(arguments)
    cex_vals = get_cex_vals(deadline_dt)

    entries = get_nft_addresses(deadline_dt)
    n = len(entries)
    nmses = {}

    for i, entry in enumerate(entries):
        nft_addr = entry
        print("=" * 60)
        print(f"NFT #{i+1}/{n}: Begin.")

        # get predicted ETH values
        print(f"nft_addr: {nft_addr}")
        pred_vals = nft_addr_to_pred_vals(nft_addr, ocean, alice)  # main call
        print(f"pred_vals: {pred_vals}")
        if len(pred_vals) != len(cex_vals):
            print("nmse = 1.0 because improper # pred_vals")
            nmses[nft_addr] = 1.0
            continue

        # calc nmse, plot
        nmse = calc_nmse(cex_vals, pred_vals)
        print(f"nft_addr={nft_addr}, nmse = {nmse}. (May become 1.0, eg if duplicates)")
        # plot_prices(cex_vals, pred_vals)

        nmses[nft_addr] = nmse
        print(f"NFT #{i+1}/{n}: Done")

    return nmses
