import json
from typing import Dict, List

import requests
from enforce_typing import enforce_types

from util.constants import AQUARIUS_BASE_URL


@enforce_types
def queryAquariusAssetNames(
    nft_dids: List[str],
) -> Dict[str, str]:
    """
    @description
      Return mapping of did -> asset name

    @params
      nft_dids -- array of dids

    @return
      did_to_asset_name -- dict of [did] : asset_name
    """

    # Remove duplicates
    nft_dids = list(set(nft_dids))

    # make a post request to Aquarius
    url = f"{AQUARIUS_BASE_URL}/api/aquarius/assets/names"

    headers = {"Content-Type": "application/json"}

    did_to_asset_name = {}

    BATCH_SIZE = 9042
    RETRY_ATTEMPTS = 3

    error_counter = 0
    # Send in chunks
    for i in range(0, len(nft_dids), BATCH_SIZE):
        # Aquarius expects "didList": ["did:op:...", ...]
        payload = json.dumps({"didList": nft_dids[i : i + BATCH_SIZE]})

        try:
            resp = requests.post(url, data=payload, headers=headers, timeout=30)
            data = json.loads(resp.text)
            did_to_asset_name.update(data)
        # pylint: disable=broad-exception-caught
        except Exception as e:
            error_counter += 1
            i -= BATCH_SIZE
            if error_counter > RETRY_ATTEMPTS:
                # pylint: disable=line-too-long, broad-exception-raised
                raise Exception(
                    f"Failed to get asset names from Aquarius after {RETRY_ATTEMPTS} attempts. Error: {e}"
                ) from e
        error_counter = 0

    return did_to_asset_name
