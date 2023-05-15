import os
from datetime import datetime, timedelta
from unittest.mock import patch

import pytest
from brownie.network import accounts

from util.judge import (
    do_get_nmses,
    get_cex_vals,
    get_nft_addresses,
    nft_addr_to_pred_vals,
    parse_arguments,
    print_address_nmse,
    print_nmses_results,
)
from util.networkutil import connect, disconnect

known_nft_addr = "0x471817de04faa9b616ed7644117d957439717bf9"
chain_id = 80001


def _get_alice_wallet():
    alice_private_key = os.getenv("REMOTE_TEST_PRIVATE_KEY1")
    alice_wallet = accounts.add(alice_private_key)
    assert alice_private_key, "need envvar REMOTE_TEST_PRIVATE_KEY1"

    return alice_wallet


def test_get_nft_addresses():
    now = datetime.now()
    less_than_a_week_ago = datetime.now() - timedelta(days=6)
    one_day_ago = datetime.now() - timedelta(days=1)
    more_than_a_week_ago = datetime.now() - timedelta(days=8)
    over_deadline = now + timedelta(minutes=1)

    with patch("gql.Client.execute") as mock:
        mock.return_value = {
            "nftTransferHistories": [
                {
                    "timestamp": less_than_a_week_ago.timestamp(),
                    "oldOwner": {"id": "0x1233"},
                },
                {"timestamp": one_day_ago.timestamp(), "oldOwner": {"id": "0x1234"}},
                {
                    "timestamp": more_than_a_week_ago.timestamp(),
                    "oldOwner": {"id": "0x456"},
                },
                {"timestamp": over_deadline.timestamp(), "oldOwner": {"id": "0x789"}},
            ]
        }
        nft_addresses = get_nft_addresses(now)

    assert "0x1233" in nft_addresses
    assert "0x1234" in nft_addresses
    assert "0x456" not in nft_addresses
    assert "0x789" not in nft_addresses


def test_get_pred_vals():
    alice_wallet = _get_alice_wallet()

    connect(chain_id)
    pred_vals = nft_addr_to_pred_vals(known_nft_addr, alice_wallet)

    assert len(pred_vals) == 12
    assert pred_vals[0] == 1633.1790360265798
    disconnect()


def test_get_cex_vals():
    deadline_dt = (datetime.today() - timedelta(days=2)).replace(
        hour=12, minute=59, second=0, microsecond=0
    )
    cex_vals = get_cex_vals(deadline_dt)
    assert len(cex_vals) == 12


def test_parse_arguments():
    with pytest.raises(SystemExit):
        parse_arguments(["dftool", "..."])

    with pytest.raises(ValueError):
        parse_arguments(["dftool", "judge", "..."])

    end_dt = parse_arguments(["dftool", "judge", "2021-09-01_12:59"])
    assert end_dt == datetime(2021, 9, 1, 12, 59)


def test_prints():
    print_address_nmse({"0x123": 0.1, "0x456": 0.2})
    print_nmses_results({"0x123": 0.1, "0x456": 0.2})


def test_do_get_nmses():
    connect(chain_id)

    with patch("util.judge.parse_arguments") as mock1:
        mock1.return_value = datetime(2021, 9, 1, 12, 59)
        with patch("util.judge.get_cex_vals") as mock2:
            mock2.return_value = [1.1, 2, 2.9, 4]
            with patch("util.judge.get_nft_addresses") as mock3:
                mock3.return_value = ["0x123", "0x456"]
                with patch("util.judge.nft_addr_to_pred_vals") as mock4:
                    mock4.side_effect = [[1, 2, 3, 4], [0, 1]]
                    nmses = do_get_nmses(["dftool", "judge", "2021-09-01_12:59"])

    disconnect()

    assert nmses["0x123"]
    assert nmses["0x456"] == 1.0
