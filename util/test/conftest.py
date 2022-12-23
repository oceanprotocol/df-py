#
# Copyright 2022 Ocean Protocol Foundation
# SPDX-License-Identifier: Apache-2.0
#
import os

from brownie.network import accounts
from enforce_typing import enforce_types
import pytest

from util.base18 import toBase18
from ocean_lib.example_config import get_config_dict
from ocean_lib.ocean.util import get_address_of_type
from ocean_lib.models.data_nft import DataNFT
from ocean_lib.models.data_nft_factory import DataNFTFactoryContract
from ocean_lib.models.datatoken import Datatoken
from ocean_lib.ocean.ocean import Ocean
from ocean_lib.web3_internal.contract_utils import get_contracts_addresses_all_networks
from ocean_lib.web3_internal.utils import connect_to_network

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

    for i in [1, 2]:
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
    return get_address_of_type(config, "Ocean")


@pytest.fixture
def OCEAN(config, OCEAN_address) -> Datatoken:
    connect_to_network("development")
    return Datatoken(config, OCEAN_address)


@pytest.fixture
def data_nft_factory(config):
    address = get_address_of_type(config, "ERC721Factory")
    return DataNFTFactoryContract(config, address)



# ========================================================================
# from ocean.py ./tests/resources/helper_functions.py
@enforce_types
def _get_wallet(index: int):
    return accounts.add(os.getenv(f"TEST_PRIVATE_KEY{index}"))


@enforce_types
def _get_ganache_wallet():
    return accounts.add(
        "0xc594c6e5def4bab63ac29eed19a134c130388f74f019bc74b8f4389df2837a58"
    )


@enforce_types
def _get_ocean_instance() -> Ocean:
    config_dict = get_config_dict()
    ocean = Ocean(config_dict)
    return ocean


# ========================================================================
@enforce_types
def alice():
    return get_wallet(1)


@enforce_types
def bob():
    return get_wallet(2)
