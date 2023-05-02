from datetime import datetime as dt, timedelta
import os
import sys
from typing import List
import requests

import ccxt
from enforce_typing import enforce_types

from predict_eth.helpers import (
    calc_nmse,
    create_alice_wallet,
    create_ocean_instance,
    filter_to_target_uts,
    print_datetime_info,
    round_to_nearest_hour,
    target_12h_unixtimes,
)
from ocean_lib.models.data_nft import DataNFT
from ocean_lib.ocean import crypto

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
def get_nft_addresses(end_dt):
    url = "https://api-testnet.polygonscan.com/api"
    params = {
        "module": "account",
        "action": "tokennfttx",
        "address": "0xA54ABd42b11B7C97538CAD7C6A2820419ddF703E",
        "apikey": os.getenv("POLYGONSCAN_API_KEY"),
    }
    result = requests.get(url, params=params).json()["result"]

    a_week_before_deadline = end_dt.now() - timedelta(weeks=1)
    addresses = []

    for result_item in result:
        result_item_date = dt.fromtimestamp(int(result_item["timeStamp"]))

        if result_item_date < a_week_before_deadline:
            continue
        if result_item_date > end_dt:
            continue

        addresses.append(result_item["contractAddress"])

    return addresses


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


def get_cex_vals(start_dt):
    target_uts = target_12h_unixtimes(start_dt)
    print_datetime_info("target times", target_uts)

    # get actual ETH values
    binance = ccxt.binanceus if os.getenv("USE_BINANCE_US", False) else ccxt.binance
    cex_x = binance().fetch_ohlcv("ETH/USDT", "1h")
    allcex_uts = [xi[0] / 1000 for xi in cex_x]
    allcex_vals = [xi[4] for xi in cex_x]
    # print_datetime_info("CEX data info", allcex_uts)
    cex_vals = filter_to_target_uts(target_uts, allcex_uts, allcex_vals)
    print(f"cex ETH price is ${cex_vals[0]} at start_dt of {start_dt}")
    print(f"cex_vals: {cex_vals}")

    return cex_vals


def parse_arguments(arguments):
    if len(arguments) != 3 or arguments[1] != "judge":
        print(HELP_JUDGE)
        sys.exit(0)

    # extract inputs
    ENDTIME_STR = arguments[2]

    end_dt = dt.strptime(ENDTIME_STR, "%Y-%m-%d_%H:%M")

    print("judging: Begin")
    print(f"Args: DEADLINE={ENDTIME_STR}")

    # specify target times
    start_dt = end_dt + timedelta(minutes=6)
    start_dt = round_to_nearest_hour(start_dt)  # so that times line up

    start_dt_str = start_dt.strftime("%Y-%m-%d_%H:%M")
    print(f"start_dt = DATETIME rounded to nearest hour = {start_dt_str}")

    return start_dt, end_dt


def print_address_nmse(nmses):
    for address, nmse in nmses.items():
        print(f"Address: {address}, NMSE: {nmse}")


def print_nmses_results(nmses, bad_nft_addrs):
    print("\n-------------")
    print("Summary:")
    print("-------------")

    print(f"{len(bad_nft_addrs)} bad entries: ")
    for bad_addr in bad_nft_addrs:
        print(f"BAD: {bad_addr}")

    print(f"\n{len(nmses)} good entries:")
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
def do_get_nmses():
    ocean = create_ocean_instance(NETWORK_NAME)
    alice_private_key = os.getenv("REMOTE_TEST_PRIVATE_KEY1")
    assert alice_private_key, "need envvar REMOTE_TEST_PRIVATE_KEY1"
    alice = create_alice_wallet(ocean)  # uses REMOTE_TEST_PRIVATE_KEY1

    start_dt, end_dt = parse_arguments(sys.argv)
    cex_vals = get_cex_vals(start_dt)

    entries = get_nft_addresses(end_dt)
    n = len(entries)
    nmses, bad_nft_addrs = {}, []

    for i, entry in enumerate(entries):
        nft_addr = entry
        print("=" * 60)
        print(f"NFT #{i+1}/{n}: Begin.")

        # get predicted ETH values
        print(f"nft_addr: {nft_addr}")
        pred_vals = nft_addr_to_pred_vals(nft_addr, ocean, alice)  # main call
        print(f"pred_vals: {pred_vals}")
        if len(pred_vals) != len(cex_vals):
            print("Error: wrong # predicted values. Skipping")
            bad_nft_addrs.append(nft_addr)
            continue

        # calc nmse, plot
        nmse = calc_nmse(cex_vals, pred_vals)
        print(f"nft_addr={nft_addr}, NMSE = {nmse:.8f}")
        # plot_prices(cex_vals, pred_vals)

        nmses[nft_addr] = nmse
        print(f"NFT #{i+1}/{n}: Done")

    return nmses, bad_nft_addrs
