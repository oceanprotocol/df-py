from datetime import datetime, timedelta
from requests.models import Response

from util.judge import get_nft_addresses
from unittest.mock import Mock, patch


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
