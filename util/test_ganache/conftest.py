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
from ocean_lib.ocean.mint_fake_ocean import mint_fake_OCEAN
from ocean_lib.ocean.util import get_address_of_type
from ocean_lib.web3_internal.contract_utils import get_contracts_addresses_all_networks
from ocean_lib.web3_internal.utils import connect_to_network

from util.base18 import toBase18, fromBase18


# ========================================================================
# from ocean.py ./conftest_ganache.py
@pytest.fixture(autouse=True)
def setup_all(request, config, OCEAN):
    # a test can skip setup_all() via decorator "@pytest.mark.nosetup_all"
    if "nosetup_all" in request.keywords:
        return

    connect_to_network("development")
    
    if not get_contracts_addresses_all_networks(config):
        print("Can not find addresses.")
        return

    accounts.clear()

    # keys 0, 1, 2 go with ocean.py values. Key 3 is arbitrary
    # (mostly to play well with mint_fake_ocean).
    from collections import OrderedDict
    private_keys = OrderedDict({
        "FACTORY_DEPLOYER_PRIVATE_KEY" : "0xc594c6e5def4bab63ac29eed19a134c130388f74f019bc74b8f4389df2837a58",
        "TEST_PRIVATE_KEY1" : "0x8467415bb2ba7c91084d932276214b11a3dd9bdb2930fefa194b666dd8020b99",
        "TEST_PRIVATE_KEY2" : "0x1d751ded5a32226054cd2e71261039b65afb9ee1c746d055dd699b1150a5befc",
        "TEST_PRIVATE_KEY3" : "0xf0fdd6852028a8cdcbb7995c717fd0649a12c45c9bd072ccf1166b02d147cc27"
    })

    # create accounts
    for private_key in private_keys.values():
        accounts.add(private_key)

    #set envvars. Will overwrite old ones
    for envvar_name, private_key in private_keys.items():
        os.environ[envvar_name] = private_key

    accounts[0].transfer(accounts[3], toBase18(10.0))

    # ensure each account has ETH
    for i, account in enumerate(accounts):
        assert account.balance() > 0, print(f"account {i} has no ETH")

    # ensure that accounts have OCEAN
    mint_fake_OCEAN(config)
    for i, account in enumerate(accounts):
        assert OCEAN.balanceOf(account) > 0, print(f"account {i} has no OCEAN")

    # amt_distribute = toBase18(1000)
    # OCEAN.mint(wallet.address, toBase18(20000), {"from": accounts[0]})

    # for account in accounts[:2]:
    #     if OCEAN.balanceOf(account) < toBase18(100):
    #         OCEAN.mint(account, amt_distribute, {"from": accounts[0]})


@pytest.fixture
def config() -> dict:
    return get_config_dict()

@pytest.fixture
def ocean() -> Ocean:
    config_dict = get_config_dict()
    return Ocean(config_dict)

@pytest.fixture
def OCEAN_address(config) -> str:
    return _addr(config, "Ocean")

@pytest.fixture
def OCEAN(config, OCEAN_address) -> Datatoken:
    return Datatoken(config, OCEAN_address)

@pytest.fixture
def data_nft_factory(config):
    return DataNFTFactoryContract(config, _addr(config, "ERC721Factory"))


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



