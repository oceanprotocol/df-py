from enforce_typing import enforce_types

from df_py.web3util.networkutil import (
    DEV_CHAINID,
    chain_id_to_address_file,
)
from df_py.web3util.oceantestutil import (
    fill_accounts_with_OCEAN,
    get_all_accounts,
)
from df_py.web3util.oceanutil import (
    calc_did,
    create_data_nft,
    create_datatoken_from_data_nft,
    ERC721Template,
    ERC20Template,
    ERC721Factory,
    FactoryRouter,
    OCEAN_token,
    OCEAN_address,
    record_deployed_contracts,
    record_dev_deployed_contracts,
)

accounts = get_all_accounts()
account0 = accounts[0]
account3 = accounts[3]


@enforce_types
def test_record_deployed_contracts():
    chain_id = DEV_CHAINID
    address_file = chain_id_to_address_file(chain_id)
    record_deployed_contracts(address_file, chain_id)
    assert OCEAN_token(chain_id)
    assert OCEAN_address(chain_id) == OCEAN_address(chain_id).lower()
    assert ERC721Template(chain_id)
    assert ERC20Template(chain_id)
    assert FactoryRouter(chain_id)
    assert ERC721Factory(chain_id)


@enforce_types
def test_OCEAN_token():
    record_dev_deployed_contracts()
    OCEAN = OCEAN_token(DEV_CHAINID)
    assert OCEAN.symbol().lower() == "ocean"


@enforce_types
def test_create_data_nft(w3):
    record_dev_deployed_contracts()
    data_nft = create_data_nft(w3, "nft_name", "nft_symbol", account0)
    assert data_nft.name() == "nft_name"
    assert data_nft.symbol() == "nft_symbol"


@enforce_types
def test_create_datatoken_from_data_nft(w3):
    record_dev_deployed_contracts()
    data_nft = create_data_nft(w3, "foo", "foo", account0)
    DT = create_datatoken_from_data_nft(w3, "dt_name", "dt_symbol", data_nft, account0)
    assert DT.name() == "dt_name"
    assert DT.symbol() == "dt_symbol"


@enforce_types
def test_calc_did():
    nft_addr = account3.address  # use a random but valid eth address
    did = calc_did(nft_addr, DEV_CHAINID)
    assert did[:7] == "did:op:"
    assert len(did) == 71


@enforce_types
def setup_function():
    fill_accounts_with_OCEAN(accounts)
