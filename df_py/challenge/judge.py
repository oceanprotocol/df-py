# adapted from https://github.com/oceanprotocol/predict-eth-judge/blob/main/pej

import os
from calendar import WEDNESDAY
from datetime import datetime, timedelta, timezone
from typing import List, Optional, Tuple

import numpy as np
from brownie.network import accounts
from enforce_typing import enforce_types

from df_py.challenge import helpers
from df_py.util import crypto, graphutil, networkutil, oceanutil
from df_py.util.get_rate import get_binance_rate

# this is the address that contestants encrypt their data to, and send to
JUDGE_ADDRESS = "0xA54ABd42b11B7C97538CAD7C6A2820419ddF703E"


@enforce_types
def _get_txs(deadline_dt) -> list:
    # https://github.com/oceanprotocol/ocean-subgraph/blob/main/schema.graphql
    a_week_before_deadline = deadline_dt - timedelta(weeks=1)

    query_s = f"""
{{nftTransferHistories(
    where: {{
             newOwner: "{JUDGE_ADDRESS.lower()}",
             timestamp_gt: {a_week_before_deadline.timestamp()},
             timestamp_lte: {deadline_dt.timestamp()}
            }}
)
    {{
        id,
        timestamp,
        nft {{
            id
        }},
        oldOwner {{
            id
        }},
        newOwner {{
            id
        }}
     }}
}}"""

    result = graphutil.submit_query(query_s, networkutil.network_to_chain_id("mumbai"))
    txs = result["nftTransferHistories"]

    return txs


@enforce_types
def _date(tx):
    ut = int(tx["timestamp"])
    return helpers.ut_to_dt(ut)


@enforce_types
def _nft_addr(tx):
    return tx["nft"]["id"]


@enforce_types
def _from_addr(tx):
    return tx["oldOwner"]["id"]


@enforce_types
def _nft_addr_to_pred_vals(nft_addr: str, judge_acct) -> List[float]:
    nft = oceanutil.get_data_nft(nft_addr)
    pred_vals_str_enc = oceanutil.get_data_field(nft, "predictions")
    try:
        pred_vals_str = crypto.asym_decrypt(pred_vals_str_enc, judge_acct.private_key)
        pred_vals = [float(s) for s in pred_vals_str[1:-1].split(",")]
    except:  # pylint: disable=W0702
        return []

    return pred_vals


def _get_cex_vals(deadline_dt: datetime) -> List[float]:
    now = datetime.now(timezone.utc)
    newest_cex_dt = deadline_dt + timedelta(minutes=1 + 12 * 5)
    print("get_cex_vals: start")
    print(f"  now           = {now} (UTC)")
    print(f"  deadline_dt   = {deadline_dt} (UTC)")
    print(f"  newest_cex_dt = {newest_cex_dt} (UTC)")
    assert deadline_dt.tzinfo == timezone.utc, "must be in UTC"
    assert deadline_dt <= now, "deadline must be past"
    assert newest_cex_dt <= now, "cex vals must be past"

    start_dt = deadline_dt + timedelta(minutes=1)
    target_dts = [
        start_dt + timedelta(minutes=_min) for _min in range(5, 5 + 12 * 5, 5)
    ]
    target_uts = [helpers.dt_to_ut(dt) for dt in target_dts]
    helpers.print_datetime_info("target times", target_uts)

    cex_vals = []
    for dt in target_dts:
        date_str = dt.strftime("%Y-%m-%d_%H:%M")
        cex_val = get_binance_rate("BTC", date_str, date_str, "TUSD", "5m")
        cex_vals.append(cex_val)

    print(f"  cex BTC price is ${cex_vals[0]} at target time 0")
    print(f"  cex_vals: {cex_vals}")

    print("get_cex_vals: done")
    return cex_vals


@enforce_types
def parse_deadline_str(deadline_str: Optional[str] = None) -> datetime:
    """
    @arguments
      deadline_str - submission deadline
        Format: YYYY-MM-DD_HOUR:MIN in UTC, or None (use most recent Wed 23:59)
        Example for Round 5: 2023-05-03_23:59
      judge_acct -- brownie account

    @return
      deadline_dt -- datetime object, in UTC
    """
    if deadline_str is None:
        today = datetime.now(timezone.utc)
        today = today.replace(hour=0, minute=0, second=0, microsecond=0)

        offset = (today.weekday() - WEDNESDAY) % 7
        prev_wed = today - timedelta(days=offset)
        deadline_dt = prev_wed.replace(hour=23, minute=59, second=0, microsecond=0)
    else:
        deadline_dt = datetime.strptime(deadline_str, "%Y-%m-%d_%H:%M")
        deadline_dt = deadline_dt.replace(tzinfo=timezone.utc)

    assert deadline_dt.tzinfo == timezone.utc, "must be in UTC"
    return deadline_dt


@enforce_types
def print_results(challenge_data):
    (from_addrs, nft_addrs, nmses) = challenge_data
    assert len(from_addrs) == len(nft_addrs) == len(nmses)
    assert nmses == sorted(nmses), "should be sorted by lowest-nmse first"

    print("\n-------------")
    print("Summary:")
    print("-------------")

    print(f"\n{len(nmses)} entries, lowest-nmse first:")
    print("-------------")
    n = len(nmses)
    for i in range(n):
        rank = i + 1
        print(
            f"#{rank:2}. NMSE: {nmses[i]:.3e}, from: {from_addrs[i]}"
            f", nft: {nft_addrs[i]}"
        )

    print("\npej: Done")


@enforce_types
def _keep_youngest_entry_per_competitor(txs: list, nmses: list) -> list:
    """For each from_addr with >1 entry, make all nmses 1.0 except youngest"""
    print()
    print("Keep-youngest: begin")
    from_addrs = [_from_addr(tx) for tx in txs]
    for from_addr in set(from_addrs):
        entries = [
            i
            for i, cand_from_addr in enumerate(from_addrs)
            if cand_from_addr == from_addr
        ]
        if len(entries) == 1:
            continue

        entries_p1 = [i + 1 for i in entries]
        print()
        print(f"  NFTs #{entries_p1} all come {from_addrs[entries[0]]}")

        dates = [_date(txs[i]) for i in entries]
        youngest_j = np.argmax(dates)
        print(f"  Youngest is #{entries_p1[youngest_j]}, at {dates[youngest_j]}")

        for j, i in enumerate(entries):
            if j != youngest_j:
                nmses[entries[j]] = 1.0
                print(
                    f"  Non-youngest #{[entries_p1[j]]}, at {dates[j]} gets nmse = 1.0"
                )
    print()
    print("Keep-youngest: done")

    return nmses


@enforce_types
def get_judge_acct():
    judge_private_key = os.getenv("JUDGE_PRIVATE_KEY")
    assert judge_private_key, "need to set envvar JUDGE_PRIVATE_KEY"

    judge_acct = accounts.add(judge_private_key)
    assert judge_acct.address.lower() == JUDGE_ADDRESS.lower(), (
        f"JUDGE_PRIVATE_KEY is wrong, it must give address={JUDGE_ADDRESS}"
        "\nGet it at private repo https://github.com/oceanprotocol/private-keys"
    )

    return judge_acct


@enforce_types
def get_challenge_data(
    deadline_dt: datetime, judge_acct
) -> Tuple[List[str], List[str], list]:
    """
    @arguments
      deadline_dt -- submission deadline, in UTC
      judge_acct -- brownie account, must have JUDGE_ADDR

    @return -- three lists, all ordered with lowest nmse first
      from_addrs -- list of [tx_i] : from_addr_str
      nft_addrs -- list of [tx_i] : nft_addr_str
      nmses -- list of [tx_i] : nmse_float_or_int
    """
    print(f"get_challenge_data: start. deadline_dt={deadline_dt}")
    assert deadline_dt.tzinfo == timezone.utc, "deadline must be in UTC"
    assert judge_acct.address.lower() == JUDGE_ADDRESS.lower()

    cex_vals = _get_cex_vals(deadline_dt)

    txs = _get_txs(deadline_dt)

    nft_addrs = [_nft_addr(tx) for tx in txs]
    from_addrs = [_from_addr(tx) for tx in txs]

    n = len(nft_addrs)
    nmses = [1.0] * n  # fill this in
    for i in range(n):
        tx, nft_addr, from_addr = txs[i], nft_addrs[i], from_addrs[i]

        print("=" * 60)
        print(f"NFT #{i+1}/{n}: Begin.")
        print(f"date = {_date(tx)}")
        print(f"from_addr = {from_addr}")
        print(f"nft_addr = {nft_addr}")

        # get predicted ETH values
        pred_vals = _nft_addr_to_pred_vals(nft_addr, judge_acct)  # main call
        print(f"pred_vals: {pred_vals}")

        if len(pred_vals) != len(cex_vals):
            nmses[i] = 1.0
            print("nmse = 1.0 because improper # pred_vals")
        else:
            nmses[i] = helpers.calc_nmse(cex_vals, pred_vals)
            # plot_prices(cex_vals, pred_vals)
            print(f"nmse = {nmses[i]:.3e}. (May become 1.0, eg if duplicates)")

        print(f"NFT #{i+1}/{n}: Done")

    # For each from_addr with >1 entry, make all nmses 1.0 except youngest
    nmses = _keep_youngest_entry_per_competitor(txs, nmses)

    # Sort results for lowest-nmse first
    entries = np.argsort(nmses)
    from_addrs = [from_addrs[i] for i in entries]
    nft_addrs = [nft_addrs[i] for i in entries]
    nmses = [nmses[i] for i in entries]

    # print
    challenge_data = (from_addrs, nft_addrs, nmses)
    print_results(challenge_data)

    # return
    print(f"get_challenge_data(): done. {len(nmses)} results")
    return challenge_data
