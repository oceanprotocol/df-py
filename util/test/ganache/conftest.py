#
# Copyright 2022 Ocean Protocol Foundation
# SPDX-License-Identifier: Apache-2.0
#
from collections import OrderedDict
import os

from brownie.network import accounts
from enforce_typing import enforce_types
import pytest
from typing import Tuple

from ocean_lib.example_config import get_config_dict
from ocean_lib.ocean.mint_fake_ocean import mint_fake_OCEAN
from ocean_lib.ocean.ocean import Ocean
from ocean_lib.web3_internal.contract_utils import get_contracts_addresses_all_networks
from ocean_lib.web3_internal.utils import connect_to_network

from util.base18 import toBase18, fromBase18


# ========================================================================
# from ocean.py ./conftest_ganache.py
@enforce_types
@pytest.fixture(autouse=True)
def setup_all(request, ocean):
    # a test can skip setup_all() via decorator "@pytest.mark.nosetup_all"
    if "nosetup_all" in request.keywords:
        return

    connect_to_network("development")

    # from brownie.network import chain, priority_fee
    # priority_fee(chain.priority_fee)
    
    if not get_contracts_addresses_all_networks(ocean.config):
        print("Can not find addresses.")
        return

    accounts.clear()

    # keys 0, 1, 2 go with ocean.py values. Key 3 is arbitrary
    # (mostly to play well with mint_fake_ocean).
    private_keys = OrderedDict({
        "FACTORY_DEPLOYER_PRIVATE_KEY" : "0xc594c6e5def4bab63ac29eed19a134c130388f74f019bc74b8f4389df2837a58",
        "TEST_PRIVATE_KEY1" : "0x8467415bb2ba7c91084d932276214b11a3dd9bdb2930fefa194b666dd8020b99",
        "TEST_PRIVATE_KEY2" : "0x1d751ded5a32226054cd2e71261039b65afb9ee1c746d055dd699b1150a5befc",
    })

    # create accounts
    for private_key in private_keys.values():
        accounts.add(private_key)

    #set envvars. Will overwrite old ones
    for envvar_name, private_key in private_keys.items():
        os.environ[envvar_name] = private_key

    # ensure each account has ETH
    for i, account in enumerate(accounts):
        assert account.balance() > 0, print(f"account {i} has no ETH")

    # ensure that accounts have OCEAN
    mint_fake_OCEAN(ocean.config)
    for i, account in enumerate(accounts):
        assert ocean.OCEAN_token.balanceOf(account) > 0, print(f"account {i} has no OCEAN")


@enforce_types
@pytest.fixture
def config() -> dict:
    return get_config_dict()

@enforce_types
@pytest.fixture
def ocean(config) -> Ocean:
    return Ocean(config)

@enforce_types
@pytest.fixture
def OCEAN_address(ocean):
    return ocean.OCEAN_address

@enforce_types
@pytest.fixture
def OCEAN(ocean):
    return ocean.OCEAN_token

@enforce_types
@pytest.fixture
def data_nft_factory(ocean):
    return ocean.data_nft_factory

@enforce_types
@pytest.fixture
def ve_allocate(ocean):
    return ocean.ve_allocate





