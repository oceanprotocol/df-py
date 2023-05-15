import os
import sys
from datetime import datetime as dt
from datetime import timedelta
from typing import List

import ccxt
from brownie.network import accounts
from enforce_typing import enforce_types
from gql import Client, gql
from gql.transport.aiohttp import AIOHTTPTransport
from web3.main import Web3

from util import crypto
from util.oceanutil import getDataField, getDataNFT
from util.predict_eth_helpers import (
    calc_nmse,
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

"""


def get_gql_client(chain_id):
    prefix = "https://v4.subgraph.mumbai.oceanprotocol.com"
    url = f"{prefix}/subgraphs/name/oceanprotocol/ocean-subgraph"
    transport = AIOHTTPTransport(url=url)

    # TODO: sleep until sync if necessary?
    try:
        client = Client(transport=transport, fetch_schema_from_transport=True)
    except Exception:
        return None

    return client


@enforce_types
def get_nft_addresses(deadline_dt):
    a_week_before_deadline = deadline_dt - timedelta(weeks=1)

    client = get_gql_client(CHAINID)
    query = gql(
        """
        {nftTransferHistories(where: {newOwner: "0xa54abd42b11b7c97538cad7c6a2820419ddf703e"}) {
          id, timestamp, oldOwner {
            id
          }, newOwner {
            id
          }
        }}
    """
    )

    txs = client.execute(query)["nftTransferHistories"]

    for tx in txs:
        tx["timestamp"] = dt.utcfromtimestamp(int(tx["timestamp"]))
        tx["contractAddress"] = tx["oldOwner"]["id"]

    filtered_txs = [
        tx for tx in txs if a_week_before_deadline < tx["timestamp"] <= deadline_dt
    ]

    return [tx["contractAddress"] for tx in filtered_txs]


@enforce_types
def nft_addr_to_pred_vals(nft_addr: str, alice) -> List[float]:
    # adapted from "What judges will do" in
    #  https://github.com/oceanprotocol/predict-eth/blob/main/challenges/main4.md

    # get predicted ETH values
    nft = getDataNFT(nft_addr)
    pred_vals_str_enc = getDataField(nft, "predictions")
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
    alice_private_key = os.getenv("REMOTE_TEST_PRIVATE_KEY1")
    alice_wallet = accounts.add(alice_private_key)
    bal = Web3.fromWei(accounts.at(alice_wallet.address).balance(), "ether")
    print(f"alice_wallet.address={alice_wallet.address}. bal={bal}")
    assert bal > 0, "Alice needs MATIC"

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
        pred_vals = nft_addr_to_pred_vals(nft_addr, alice_wallet)  # main call
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
