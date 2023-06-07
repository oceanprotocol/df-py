import requests

from df_py.util import networkutil


def submitQuery(query: str, chainID: int) -> dict:
    subgraph_url = networkutil.chainIdToSubgraphUri(chainID)
    request = requests.post(subgraph_url, "", json={"query": query}, timeout=30)
    if request.status_code != 200:
        # pylint: disable=broad-exception-raised
        raise Exception(f"Query failed. Return code is {request.status_code}\n{query}")

    result = request.json()

    return result
