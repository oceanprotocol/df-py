import os
import sys
from calendar import WEDNESDAY
from datetime import datetime, timedelta, timezone
from typing import List

import ccxt
from brownie.network import accounts
from enforce_typing import enforce_types
import gql
from gql.transport.aiohttp import AIOHTTPTransport

from util import crypto, oceanutil
from util.challenge import helpers


@enforce_types
def parse_deadline_str(deadline_str: str) -> datetime:
    """
    @arguments
      deadline_str - submission deadline
        Format: YYYY-MM-DD_HOUR:MIN in UTC, or None (use most recent Wed 23:59)
        Example for Round 5: 2023-05-03_23:59
      judge_acct -- brownie account

    @return
      deadline_dt -- datetime object
    """
    if deadline_str == "None":
        today = datetime.now(timezone.utc)
        today = today.replace(hour=0, minute=0, second=0, microsecond=0)
    
        offset = (today.weekday() - WEDNESDAY) % 7
        prev_wed = today - timedelta(days=offset)
        deadline_dt = prev_wed.replace(
            hour=23, minute=59, second=0, microsecond=0)
        return deadline_dt
    
    deadline_dt = datetime.strptime(deadline_str, "%Y-%m-%d_%H:%M")
    return deadline_dt


@enforce_types
def _nft_addr_to_pred_vals(nft_addr: str, judge_acct) -> List[float]:
    nft = oceanutil.getDataNFT(nft_addr)
    pred_vals_str_enc = oceanutil.getDataField(nft, "predictions")
    try:
        pred_vals_str = crypto.asym_decrypt(pred_vals_str_enc, judge_acct.private_key)
        pred_vals = [float(s) for s in pred_vals_str[1:-1].split(",")]
    except:  # pylint: disable=W0702
        return []

    return pred_vals


@enforce_types
def _get_cex_vals(deadline_dt):
    target_uts = helpers.target_12h_unixtimes(deadline_dt + timedelta(minutes=1))
    helpers.print_datetime_info("target times", target_uts)

    cex_x = ccxt.kraken().fetch_ohlcv("ETH/USDT", "5m")
    allcex_uts = [xi[0] / 1000 for xi in cex_x]
    allcex_vals = [xi[4] for xi in cex_x]
    helpers.print_datetime_info("CEX data info", allcex_uts)

    cex_vals = helpers.filter_to_target_uts(target_uts, allcex_uts, allcex_vals)
    print(f"cex ETH price is ${cex_vals[0]} at target time 0")
    print(f"cex_vals: {cex_vals}")

    return cex_vals


@enforce_types
def _print_address_nmse(nmses):
    for address, nmse in nmses.items():
        print(f"Address: {address}, NMSE: {nmse}")


@enforce_types
def _print_nmses_results(nmses):
    print("\n-------------")
    print("Summary:")
    print("-------------")

    print(f"\n{len(nmses)} entries:")
    _print_address_nmse(nmses)

    ranking = dict(sorted(nmses.items(), key=lambda item: item[1]))
    print("\nafter ranking:")
    print("-------------")
    _print_address_nmse(ranking)

    print("\ntop 3:")
    print("-------------")
    print("\n".join(list(ranking.keys())[:3]))

    print("\njudge: Done")


def _get_gql_client(chainid: int):
    assert chainid == 80001, "only polygon-test (mumbai) is supported"

    prefix = "https://v4.subgraph.mumbai.oceanprotocol.com"
    url = f"{prefix}/subgraphs/name/oceanprotocol/ocean-subgraph"
    transport = AIOHTTPTransport(url=url)

    client = gql.Client(transport=transport, fetch_schema_from_transport=True)
    return client


@enforce_types
def _get_nft_addresses(deadline_dt, chainid:int):
    a_week_before_deadline = deadline_dt - timedelta(weeks=1)

    client = _get_gql_client(chainid)
    where = """where: {newOwner: "0xa54abd42b11b7c97538cad7c6a2820419ddf703e","""
    where += f"""
        timestamp_gt: {a_week_before_deadline.timestamp()},
        timestamp_lte: {deadline_dt.timestamp()}
    """
    where += "}"

    query = gql.gql(
        """
        {nftTransferHistories("""
        + where
        + """) {
          id, timestamp, oldOwner {
            id
          }, newOwner {
            id
          }
        }}
    """
    )

    txs = client.execute(query)["nftTransferHistories"]

    return [tx["oldOwner"]["id"] for tx in txs]



@enforce_types
def get_nmses(deadline_dt: datetime, judge_acct):
    """
    @arguments
      deadline_dt -- submission deadline
      judge_acct -- brownie account

    @return
      nmses -- dict of [nft_addr_str] : nmse_float
    """
    cex_vals = _get_cex_vals(deadline_dt)

    entries = _get_nft_addresses(deadline_dt)
    n = len(entries)
    nmses = {}

    for i, entry in enumerate(entries):
        nft_addr = entry
        print("=" * 60)
        print(f"NFT #{i+1}/{n}: Begin.")

        # get predicted ETH values
        print(f"nft_addr: {nft_addr}")
        pred_vals = _nft_addr_to_pred_vals(nft_addr, judge_acct)  # main call
        print(f"pred_vals: {pred_vals}")
        if len(pred_vals) != len(cex_vals):
            print("nmse = 1.0 because improper # pred_vals")
            nmses[nft_addr] = 1.0
            continue

        # calc nmse, plot
        nmse = helpers.calc_nmse(cex_vals, pred_vals)
        print(f"nft_addr={nft_addr}, nmse={nmse}. (May become 1.0, eg if duplicates)")
        # plot_prices(cex_vals, pred_vals)

        nmses[nft_addr] = nmse
        print(f"NFT #{i+1}/{n}: Done")

    return nmses



