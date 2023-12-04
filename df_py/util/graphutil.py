import time

import requests

from df_py.util import networkutil

MAX_WAIT = 60 * 10


def submit_query(query: str, chainID: int) -> dict:
    subgraph_url = networkutil.chain_id_to_subgraph_uri(chainID)
    request = requests.post(subgraph_url, "", json={"query": query}, timeout=30)

    if request.status_code != 200:
        # pylint: disable=broad-exception-raised
        raise Exception(f"Query failed. Return code is {request.status_code}\n{query}")

    result = request.json()

    return result


def get_last_block(chain_id: int) -> int:
    query = "{_meta { block { number } } }"
    result = submit_query(query, chain_id)

    return result["data"]["_meta"]["block"]["number"]


def wait_to_latest_block(chain_id: int, max_wait: int = MAX_WAIT):
    if chain_id in networkutil.OBSOLETED_CHAIN_IDS:
        return

    web3 = networkutil.chain_id_to_web3(chain_id)
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
