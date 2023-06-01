import gql
import requests
from gql.transport.aiohttp import AIOHTTPTransport

from util import networkutil


def submitQuery(query: str, chainID: int) -> dict:
    subgraph_url = networkutil.chainIdToSubgraphUri(chainID)
    request = requests.post(subgraph_url, "", json={"query": query}, timeout=30)
    if request.status_code != 200:
        # pylint: disable=broad-exception-raised
        raise Exception(f"Query failed. Return code is {request.status_code}\n{query}")

    result = request.json()

    return result


def get_gql_client():
    # note: only supports mumbai right now

    prefix = "https://v4.subgraph.mumbai.oceanprotocol.com"
    url = f"{prefix}/subgraphs/name/oceanprotocol/ocean-subgraph"
    transport = AIOHTTPTransport(url=url)

    client = gql.Client(transport=transport, fetch_schema_from_transport=True)
    return client
