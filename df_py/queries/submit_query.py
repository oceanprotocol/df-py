from enforce_typing import enforce_types
import requests

from df_py.web3util.networkutil import chain_id_to_subgraph_uri


@enforce_types
def submit_query(query: str, chainID: int) -> dict:
    subgraph_url = chain_id_to_subgraph_uri(chainID)
    request = requests.post(subgraph_url, "", json={"query": query}, timeout=30)

    if request.status_code != 200:
        # pylint: disable=broad-exception-raised
        raise Exception(f"Query failed. Return code is {request.status_code}\n{query}")

    result = request.json()

    return result
