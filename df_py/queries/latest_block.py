import time

from enforce_typing import enforce_types
import requests

from df_py.web3util.networkutil import (
    OBSOLETED_CHAIN_IDS,
    chain_id_to_web3,
)

MAX_WAIT = 60 * 15


@enforce_types
def get_last_block(chain_id: int) -> int:
    """Get the last block that was synced to the subgraph."""
    query = "{_meta { block { number } } }"
    result = submit_query(query, chain_id)

    return result["data"]["_meta"]["block"]["number"]


@enforce_types
def wait_to_latest_block(chain_id: int, max_wait: int = MAX_WAIT):
    """Wait until the subgraph is synced to the latest block on the chain."""
    if chain_id in OBSOLETED_CHAIN_IDS:
        return

    web3 = chain_id_to_web3(chain_id)
    block_number = web3.eth.get_block("latest")["number"]

    last_block = -1

    start_time = time.time()

    while last_block < block_number:
        print(f"Waiting for sync with subgraph, currently at last block {last_block}.")

        try:
            last_block = get_last_block(chain_id)
        except KeyError:
            pass

        time.sleep(2)

        if time.time() - start_time > max_wait:
            raise Exception(
                f"Waited for {MAX_WAIT} seconds for block {block_number} "
                "to be synced, but it never was."
            )
