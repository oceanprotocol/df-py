from datetime import datetime, timedelta, timezone
from unittest.mock import patch

import numpy as np
from enforce_typing import enforce_types

from df_py.challenge import judge
from df_py.util import networkutil


def test_get_txs():
    now = datetime.now().replace(tzinfo=timezone.utc)

    six_days_ago = now - timedelta(days=6)
    one_day_ago = now - timedelta(days=1)

    with patch("df_py.util.graphutil.submitQuery") as mock:
        mock.return_value = {
            "nftTransferHistories": [
                {
                    "timestamp": six_days_ago.timestamp(),
                    "nft": {"id": "0xnft1"},
                    "oldOwner": {"id": "0xfrom1"},
                },
                {
                    "timestamp": one_day_ago.timestamp(),
                    "nft": {"id": "0xnft2"},
                    "oldOwner": {"id": "0xfrom2"},
                },
            ]
        }
        txs = judge._get_txs(now)

    # sort txs by nft address, to ease subsequent testing
    nft_addrs = [tx["nft"]["id"] for tx in txs]
    I = np.argsort(nft_addrs)
    txs = [txs[i] for i in I]

    # now test
    nft_addrs = [tx["nft"]["id"] for tx in txs]
    from_addrs = [tx["oldOwner"]["id"] for tx in txs]

    assert nft_addrs == ["0xnft1", "0xnft2"]
    assert from_addrs == ["0xfrom1", "0xfrom2"]


@enforce_types
def test_nft_addr_to_pred_vals():
    mumbai_chainid = 80001
    known_nft_addr = "0x471817de04faa9b616ed7644117d957439717bf9"

    networkutil.connect(mumbai_chainid)
    judge_acct = judge.get_judge_acct()
    pred_vals = judge._nft_addr_to_pred_vals(known_nft_addr, judge_acct)

    assert len(pred_vals) == 12
    assert pred_vals[0] == 1633.1790360265798

    with patch("df_py.challenge.judge.crypto.asym_decrypt") as mock:
        mock.side_effect = Exception("mocked exception")
        pred_vals = judge._nft_addr_to_pred_vals(known_nft_addr, judge_acct)

    assert pred_vals == []

    networkutil.disconnect()


@enforce_types
def test_get_cex_vals1():
    today = datetime.today().replace(tzinfo=timezone.utc)
    deadline_dt = today - timedelta(days=2)
    deadline_dt = deadline_dt.replace(hour=12, minute=59, second=0, microsecond=0)
    cex_vals = judge._get_cex_vals(deadline_dt)
    assert len(cex_vals) == 12


@enforce_types
def test_get_cex_vals2():
    deadline_dt = datetime(2023, 5, 3, 23, 59, tzinfo=timezone.utc)
    cex_vals = judge._get_cex_vals(deadline_dt)
    assert len(cex_vals) == 12


@enforce_types
def test_parse_deadline_str1():
    dt = judge.parse_deadline_str("2023-05-03_23:59")
    dt_target = datetime(2023, 5, 3, 23, 59, tzinfo=timezone.utc)
    assert dt == dt_target


@enforce_types
def test_parse_deadline_str2():
    dt = judge.parse_deadline_str()

    assert (datetime.now(timezone.utc) - dt) < timedelta(days=7)  # within 1 wk
    assert dt.weekday() == 2  # Mon is 0, Tue is 1, Wed is 2
    assert dt.hour == 23
    assert dt.minute == 59
    assert dt.second == 0
    assert dt.microsecond == 0


@enforce_types
def test_print_results():
    from_addrs = ["0xfrom1", "0xfrom2"]
    nft_addrs = ["0xnft1", "0xnft2"]
    nmses = [0.2, 1.0]
    challenge_data = (from_addrs, nft_addrs, nmses)
    judge.print_results(challenge_data)


@enforce_types
def test_get_judge_acct():
    judge_acct = judge.get_judge_acct()
    assert judge_acct.address == judge.JUDGE_ADDRESS


@enforce_types
def test_get_challenge_data():
    dt = datetime(2021, 9, 1, 12, 59, tzinfo=timezone.utc)
    judge_acct = judge.get_judge_acct()

    with patch("df_py.challenge.judge._get_cex_vals") as mock1:
        cex_vals = list(0.1 + np.arange(0.0, 12.0, 1.0))
        assert len(cex_vals) == 12
        mock1.return_value = cex_vals
        with patch("df_py.challenge.judge._get_txs") as mock2:
            tx1 = {
                "timestamp": 1683790437.215631,
                "nft": {"id": "0xnft1"},
                "oldOwner": {"id": "0xfrom1"},
            }
            tx2 = {
                "timestamp": 1684222437.215636,
                "nft": {"id": "0xnft2"},
                "oldOwner": {"id": "0xfrom2"},
            }
            # tx1, but earlier. Will be discarded by keep youngest entry logic
            tx3 = {
                "timestamp": 1683790430,
                "nft": {"id": "0xnft3"},
                "oldOwner": {"id": "0xfrom1"},
            }
            mock2.return_value = [tx1, tx2, tx3]

            with patch("df_py.challenge.judge._nft_addr_to_pred_vals") as mock3:
                # 0x123 has correct length. 0x456 doesn't, so its nmse = 1.0
                predvals_0x123 = list(0.11 + np.arange(0.0, 12.0, 1.0))
                predvals_0x456 = [0.2, 0.4]
                assert len(predvals_0x123) == len(cex_vals)
                assert len(predvals_0x456) != len(cex_vals)
                mock3.side_effect = [predvals_0x123, predvals_0x456, predvals_0x123]
                challenge_data = judge.get_challenge_data(dt, judge_acct)

    (from_addrs, nft_addrs, nmses) = challenge_data

    assert nmses[2] == 1.0  # using keep youngest entry logic

    assert nmses == sorted(nmses), "should be sorted by lowest-nmse first"
    assert nmses[0] != 1.0
    assert nmses[1] == 1.0

    # should we elliminate the second entry from 0xfrom1?
    assert from_addrs == ["0xfrom1", "0xfrom2", "0xfrom1"]
    assert nft_addrs == ["0xnft1", "0xnft2", "0xnft3"]
