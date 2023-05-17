import os
from datetime import date, datetime, timedelta, timezone
from unittest.mock import patch

import pytest
from brownie.network import accounts
import numpy as np

from util import networkutil
from util.base18 import from_wei
from util.challenge import judge

MUMBAI_CHAINID = 80001
KNOWN_NFT_ADDR = "0x471817de04faa9b616ed7644117d957439717bf9" #on mumbai


def test_parse_deadline_str__fixed():
    dt = judge.parse_deadline_str("2023-05-03_23:59")
    dt_target = datetime(2023, 5, 3, 23, 59)
    assert dt == dt_target
        
    
def test_parse_deadline_str__None():
    dt = judge.parse_deadline_str("None")

    assert (datetime.now(timezone.utc) - dt) < timedelta(days=7) # within 1 wk
    assert dt.weekday() == 2 # Mon is 0, Tue is 1, Wed is 2
    assert dt.hour == 23
    assert dt.minute == 59
    assert dt.second == 0
    assert dt.microsecond == 0


def test_nft_addr_to_pred_vals():
    networkutil.connect(MUMBAI_CHAINID)
    judge_acct = _get_judge_acct()
    pred_vals = judge._nft_addr_to_pred_vals(KNOWN_NFT_ADDR, judge_acct)

    assert len(pred_vals) == 12
    assert pred_vals[0] == 1633.1790360265798
    networkutil.disconnect()


def test_get_cex_vals():
    deadline_dt = (datetime.today() - timedelta(days=2)).replace(
        hour=12, minute=59, second=0, microsecond=0
    )
    cex_vals = judge._get_cex_vals(deadline_dt)
    assert len(cex_vals) == 12


def test_print_address_nmse():
    judge._print_address_nmse({"0x123": 0.1, "0x456": 0.2})


def test_print_nmses_results():
    judge._print_nmses_results({"0x123": 0.1, "0x456": 0.2})


def test_get_nft_addresses():
    now = datetime.now()
    less_than_a_week_ago = datetime.now() - timedelta(days=6)
    one_day_ago = datetime.now() - timedelta(days=1)

    with patch("gql.Client.execute") as mock:
        mock.return_value = {
            "nftTransferHistories": [
                {
                    "timestamp": less_than_a_week_ago.timestamp(),
                    "oldOwner": {"id": "0x1233"},
                },
                {"timestamp": one_day_ago.timestamp(), "oldOwner": {"id": "0x1234"}},
            ]
        }
        nft_addresses = judge._get_nft_addresses(now, MUMBAI_CHAINID)

    assert "0x1233" in nft_addresses
    assert "0x1234" in nft_addresses
    

def test_get_nmses():
    networkutil.connect(MUMBAI_CHAINID)
    
    dt = datetime(2021, 9, 1, 12, 59)
    judge_acct = _get_judge_acct()

    with patch("util.challenge.judge._get_cex_vals") as mock2:
        cex_vals = list(0.1 + np.arange(0.0, 12.0, 1.0))
        assert len(cex_vals) == 12
        mock2.return_value = cex_vals
        with patch("util.challenge.judge._get_nft_addresses") as mock3:
            mock3.return_value = ["0x123", "0x456"]
            with patch("util.challenge.judge._nft_addr_to_pred_vals") as mock4:
                # 0x123 has correct length. 0x456 doesn't, so its nmse = 1.0
                predvals_0x123 = list(0.11 + np.arange(0.0, 12.0, 1.0))
                predvals_0x456 = [0.2, 0.4]
                assert len(predvals_0x123) == len(cex_vals)
                assert len(predvals_0x456) != len(cex_vals)
                mock4.side_effect = [predvals_0x123, predvals_0x456]
                nmses = judge.get_nmses(dt, judge_acct)

    networkutil.disconnect()

    assert nmses["0x123"] != 1.0
    assert nmses["0x456"] == 1.0


def _get_judge_acct():
    judge_private_key = os.getenv("JUDGE_PRIVATE_KEY")
    assert judge_private_key, "need envvar JUDGE_PRIVATE_KEY"
    
    judge_acct = accounts.add(judge_private_key)
    bal = from_wei(judge_acct.balance())
    print(f"judge_acct.address={judge_acct.address}, bal={bal}")
    assert bal > 0, "Judge_Acct needs MATIC"
    return judge_acct
    
