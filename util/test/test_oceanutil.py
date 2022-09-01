import brownie
from enforce_typing import enforce_types

from util.oceanutil import (
    recordDeployedContracts,
    OCEANtoken,
    createDataNFT,
    createDatatokenFromDataNFT,
    calcDID,
)
from util import networkutil, oceantestutil, oceanutil

account0, account3 = None, None

CHAINID = networkutil.DEV_CHAINID
ADDRESS_FILE = networkutil.chainIdToAddressFile(CHAINID)


@enforce_types
def test_recordDeployedContracts():
    recordDeployedContracts(ADDRESS_FILE)
    assert oceanutil.OCEANtoken()
    assert oceanutil.OCEAN_address() == oceanutil.OCEAN_address().lower()
    assert oceanutil.ERC721Template()
    assert oceanutil.ERC20Template()
    assert oceanutil.factoryRouter()
    assert oceanutil.Staking()
    assert oceanutil.ERC721Factory()


@enforce_types
def test_OCEANtoken():
    recordDeployedContracts(ADDRESS_FILE)
    OCEAN = OCEANtoken()
    assert OCEAN.symbol().lower() == "ocean"


@enforce_types
def test_createDataNFT():
    recordDeployedContracts(ADDRESS_FILE)
    data_NFT = createDataNFT("nft_name", "nft_symbol", account0)
    assert data_NFT.name() == "nft_name"
    assert data_NFT.symbol() == "nft_symbol"


@enforce_types
def test_createDatatokenFromDataNFT():
    recordDeployedContracts(ADDRESS_FILE)
    data_NFT = createDataNFT("foo", "foo", account0)
    DT = createDatatokenFromDataNFT("dt_name", "dt_symbol", data_NFT, account0)
    assert DT.name() == "dt_name"
    assert DT.symbol() == "dt_symbol"


@enforce_types
def test_calcDID():
    nft_addr = account3.address  # use a random but valid eth address
    did = calcDID(nft_addr, CHAINID)
    assert did[:7] == "did:op:"
    assert len(did) == 71


@enforce_types
def setup_function():
    networkutil.connect(CHAINID)
    global account0, account3
    account0 = brownie.network.accounts[0]
    account3 = brownie.network.accounts[3]
    oceanutil.recordDeployedContracts(ADDRESS_FILE)
    oceantestutil.fillAccountsWithOCEAN()


@enforce_types
def teardown_function():
    networkutil.disconnect()
