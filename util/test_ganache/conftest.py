#
# Copyright 2022 Ocean Protocol Foundation
# SPDX-License-Identifier: Apache-2.0
#
import os

from brownie.network import accounts
from enforce_typing import enforce_types
import pytest
from typing import Tuple

from ocean_lib.example_config import get_config_dict
from ocean_lib.models.arguments import DataNFTArguments, DatatokenArguments
from ocean_lib.models.data_nft import DataNFT
from ocean_lib.models.data_nft_factory import DataNFTFactoryContract
from ocean_lib.models.datatoken import Datatoken
from ocean_lib.ocean.ocean import Ocean
from ocean_lib.ocean.util import get_address_of_type
from ocean_lib.web3_internal.contract_utils import get_contracts_addresses_all_networks
from ocean_lib.web3_internal.utils import connect_to_network

from util.base18 import toBase18, fromBase18

_NETWORK = "ganache"


# ========================================================================
# from ocean.py ./conftest_ganache.py
@pytest.fixture(autouse=True)
def setup_all(request, config, OCEAN):
    connect_to_network("development")
    accounts.clear()

    # a test can skip setup_all() via decorator "@pytest.mark.nosetup_all"
    if "nosetup_all" in request.keywords:
        return

    wallet = _get_ganache_wallet()
    
    if not wallet:
        return

    if not get_contracts_addresses_all_networks(config):
        print("Can not find addresses.")
        return

    assert wallet.balance() >= toBase18(10), "need more eth"
    
    amt_distribute = toBase18(1000)
    OCEAN.mint(wallet.address, toBase18(20000), {"from": wallet})

    for i in range(1, 5):
        w = _get_wallet(i)
        if w.balance() < toBase18(2):
            wallet.transfer(w, toBase18(4))

        if OCEAN.balanceOf(w) < toBase18(100):
            OCEAN.mint(w, amt_distribute, {"from": wallet})


@pytest.fixture
def config():
    return get_config_dict()

@pytest.fixture
def ocean():
    return _get_ocean_instance()

@pytest.fixture
def OCEAN_address(config) -> str:
    return _addr(config, "Ocean")

@pytest.fixture
def OCEAN(config, OCEAN_address) -> Datatoken:
    connect_to_network("development")
    return Datatoken(config, OCEAN_address)

@pytest.fixture
def data_nft_factory(config):
    return DataNFTFactoryContract(config, _addr(config, "ERC721Factory"))

@pytest.fixture
def data_NFT_and_DT(ocean, alice) -> Tuple[DataNFT, Datatoken]:
    data_NFT = ocean.data_nft_factory.create(DataNFTArguments('1','1'), alice)
    DT = data_NFT.create_datatoken(DatatokenArguments('1','1'), alice)
    return (data_NFT, DT)

@pytest.fixture
def data_NFT(data_NFT_and_DT) -> DataNFT:
    return data_NFT_and_DT[0]

@pytest.fixture
def DT(data_NFT_and_DT) -> Datatoken:
    return data_NFT_and_DT[1]


# ========================================================================
@pytest.fixture
def alice():
    return _get_wallet(1)


@pytest.fixture
def bob():
    return _get_wallet(2)

# ========================================================================
# replace these with ocean.df_rewards() etc once ocean.py supports (#1235)
#  -as of Dec 23, 2022 there's an ocean.py PR (#1236)
from ocean_lib.web3_internal.contract_base import ContractBase

class DFStrategyV1(ContractBase):
    CONTRACT_NAME = "DFStrategyV1"
    
class DFRewards(ContractBase):
    CONTRACT_NAME = "DFRewards"

@pytest.fixture
def df_rewards(config) -> DFRewards:
    return DFRewards(config, _addr(config, "DFRewards"))

@pytest.fixture
def df_strategy_v1(config) -> DFStrategyV1:
    return DFStrategyV1(config, _addr(config, "DFRewards"))

@pytest.fixture
def df_strategy(df_strategy_v1) -> DFStrategyV1: # alias for df_strategy_v1
    return df_strategy_v1

@enforce_types
def _addr(config: dict, type_str: str):
    return get_address_of_type(config, type_str)


# ========================================================================
# from ocean.py ./tests/resources/helper_functions.py
_WALLETS = {}
_DEFAULT_KEYS = [
    "0xc594c6e5def4bab63ac29eed19a134c130388f74f019bc74b8f4389df2837a58",
    "0x8467415bb2ba7c91084d932276214b11a3dd9bdb2930fefa194b666dd8020b99",
    "0x1d751ded5a32226054cd2e71261039b65afb9ee1c746d055dd699b1150a5befc"
]
@enforce_types
def _get_wallet(index: int):
    global _WALLETS, _DEFAULT_KEYS

    if index not in _WALLETS:    
        private_key = os.getenv(f"TEST_PRIVATE_KEY{index}")
        if not private_key and index < len(_DEFAULT_KEYS):
            private_key = _DEFAULT_KEYS[index]
            
        if private_key:
            _WALLETS[index] = accounts.add(private_key)
        else:
            _WALLETS[index] = accounts.add()

    return _WALLETS[index]


@enforce_types
def _get_ganache_wallet():
    return _get_wallet(0)


@enforce_types
def _get_ocean_instance() -> Ocean:
    config_dict = get_config_dict()
    ocean = Ocean(config_dict)
    return ocean
