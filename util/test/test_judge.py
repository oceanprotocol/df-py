import os
from datetime import datetime, timedelta
from unittest.mock import Mock, patch

from predict_eth.helpers import create_alice_wallet, create_ocean_instance
from requests.models import Response

from util.judge import get_nft_addresses, nft_addr_to_pred_vals


def test_get_nft_addresses():
    now = datetime.now()
    less_than_a_week_ago = datetime.now() - timedelta(days=6)
    one_day_ago = datetime.now() - timedelta(days=1)
    more_than_a_week_ago = datetime.now() - timedelta(days=8)
    over_deadline = now + timedelta(minutes=1)

    with patch("requests.get") as mock:
        the_response = Mock(spec=Response)
        the_response.json.return_value = {
            "result": [
                {
                    "timeStamp": less_than_a_week_ago.timestamp(),
                    "contractAddress": "0x1233",
                },
                {"timeStamp": one_day_ago.timestamp(), "contractAddress": "0x1234"},
                {
                    "timeStamp": more_than_a_week_ago.timestamp(),
                    "contractAddress": "0x456",
                },
                {"timeStamp": over_deadline.timestamp(), "contractAddress": "0x789"},
            ]
        }
        mock.return_value = the_response
        nft_addresses = get_nft_addresses(now)

    assert "0x1233" in nft_addresses
    assert "0x1234" in nft_addresses
    assert "0x456" not in nft_addresses
    assert "0x789" not in nft_addresses


def test_get_pred_vals():
    ocean = create_ocean_instance("polygon-test")
    alice_private_key = os.getenv("REMOTE_TEST_PRIVATE_KEY1")
    assert alice_private_key, "need envvar REMOTE_TEST_PRIVATE_KEY1"
    alice = create_alice_wallet(ocean)  # uses REMOTE_TEST_PRIVATE_KEY1

    pred_vals = nft_addr_to_pred_vals(
        "0x471817de04faa9b616ed7644117d957439717bf9", ocean, alice
    )

    assert len(pred_vals) == 12
    assert pred_vals[0] == 1633.1790360265798
