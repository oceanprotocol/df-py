from enforce_typing import enforce_types
import requests


@enforce_types
def oceanSubgraphUrl(subgraph_uri: str) -> str:
    """subgraph_uri -- e.g. for barge http://127.0.0.1:9000"""
    return subgraph_uri + "/subgraphs/name/oceanprotocol/ocean-subgraph"


@enforce_types
def submitQuery(query: str, subgraph_url: str) -> str:
    request = requests.post(subgraph_url, "", json={"query": query})
    if request.status_code != 200:
        raise Exception(f"Query failed. Return code is {request.status_code}\n{query}")

    result = request.json()

    return result
