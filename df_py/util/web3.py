import os

from enforce_typing import enforce_types
from web3.exceptions import ExtraDataLengthError
from web3.main import Web3
from web3.middleware import geth_poa_middleware

from df_py.util.http_provider import get_web3_connection_provider


@enforce_types
def get_web3(network_url: str) -> Web3:
    provider = get_web3_connection_provider(network_url)
    web3 = Web3(provider)

    try:
        web3.eth.get_block("latest")
    except ExtraDataLengthError:
        web3.middleware_onion.inject(geth_poa_middleware, layer=0)

    web3.strict_bytes_type_checking = False
    return web3


def get_rpc_url(network_name: str) -> str:
    """Return the RPC URL for a given network."""
    base_url = None
    converted_network_name = network_name.upper().replace("-", "_")

    if os.getenv(f"{converted_network_name}_RPC_URL"):
        base_url = os.getenv(f"{converted_network_name}_RPC_URL")

    if os.getenv("WEB3_INFURA_PROJECT_ID") and base_url:
        infura_networks = [
            nt.lower() for nt in os.getenv("INFURA_NETWORKS", "").split(",")
        ]

        if network_name.lower() in infura_networks or "all" in infura_networks:
            base_url = f"{base_url}{os.getenv('WEB3_INFURA_PROJECT_ID')}"

    if base_url:
        return base_url

    raise ValueError(f"Need to set {converted_network_name}_RPC_URL env variable.")
