import os

from enforce_typing import enforce_types
from eth_account import Account

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

accounts = [
    Account.from_key(private_key=os.getenv(f"TEST_PRIVATE_KEY{index}"))
    for index in range(0, 9)
]

account0 = accounts[0]
account3 = accounts[3]


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
def test_create_data_nft(w3):
    record_deployed_contracts(ADDRESS_FILE)
    data_nft = create_data_nft(w3, "nft_name", "nft_symbol", account0)
    assert data_nft.name() == "nft_name"
    assert data_nft.symbol() == "nft_symbol"


@enforce_types
def test_create_datatoken_from_data_nft(w3):
    record_deployed_contracts(ADDRESS_FILE)
    data_nft = create_data_nft(w3, "foo", "foo", account0)
    DT = create_datatoken_from_data_nft(w3, "dt_name", "dt_symbol", data_nft, account0)
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
    oceantestutil.fill_accounts_with_OCEAN(accounts)
