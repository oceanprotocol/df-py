import brownie
from enforce_typing import enforce_types

from df_py.util import networkutil, oceantestutil, oceanutil
from df_py.util.oceanutil import (
    OCEAN_token,
    calc_did,
    create_data_nft,
    create_datatoken_from_data_nft,
    record_deployed_contracts,
)

account0, account3 = None, None

CHAINID = networkutil.DEV_CHAINID
ADDRESS_FILE = networkutil.chain_id_to_address_file(CHAINID)


@enforce_types
def test_record_deployed_contracts():
    record_deployed_contracts(ADDRESS_FILE)
    assert oceanutil.OCEAN_token()
    assert oceanutil.OCEAN_address() == oceanutil.OCEAN_address().lower()
    assert oceanutil.ERC721Template()
    assert oceanutil.ERC20Template()
    assert oceanutil.FactoryRouter()
    assert oceanutil.Staking()
    assert oceanutil.ERC721Factory()


@enforce_types
def test_OCEAN_token():
    record_deployed_contracts(ADDRESS_FILE)
    OCEAN = OCEAN_token()
    assert OCEAN.symbol().lower() == "ocean"


@enforce_types
def test_create_data_nft():
    record_deployed_contracts(ADDRESS_FILE)
    data_NFT = create_data_nft("nft_name", "nft_symbol", account0)
    assert data_NFT.name() == "nft_name"
    assert data_NFT.symbol() == "nft_symbol"


@enforce_types
def test_create_datatoken_from_data_nft():
    record_deployed_contracts(ADDRESS_FILE)
    data_NFT = create_data_nft("foo", "foo", account0)
    DT = create_datatoken_from_data_nft("dt_name", "dt_symbol", data_NFT, account0)
    assert DT.name() == "dt_name"
    assert DT.symbol() == "dt_symbol"


@enforce_types
def test_calc_did():
    nft_addr = account3.address  # use a random but valid eth address
    did = calc_did(nft_addr, CHAINID)
    assert did[:7] == "did:op:"
    assert len(did) == 71


@enforce_types
def setup_function():
    networkutil.connect(CHAINID)
    global account0, account3
    account0 = brownie.network.accounts[0]
    account3 = brownie.network.accounts[3]
    oceanutil.record_deployed_contracts(ADDRESS_FILE)
    oceantestutil.fill_accounts_with_OCEAN()


@enforce_types
def teardown_function():
    networkutil.disconnect()
