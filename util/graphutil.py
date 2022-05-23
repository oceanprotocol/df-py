import requests

from util import chainlist


def submitQuery(query: str, chainID: int) -> dict:
    subgraph_url = chainlist.chainIdToSubgraphUri(chainID)
    request = requests.post(subgraph_url, "", json={"query": query})
    if request.status_code != 200:
        raise Exception(f"Query failed. Return code is {request.status_code}\n{query}")

    result = request.json()

    return result
