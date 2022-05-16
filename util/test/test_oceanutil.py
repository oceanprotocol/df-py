import brownie
from enforce_typing import enforce_types

from util.oceanutil import recordDeployedContracts, OCEANtoken, \
    createDataNFT, createDatatokenFromDataNFT, createBPoolFromDatatoken, \
    calcDID
from util import chainlist, oceanutil
from util.base18 import fromBase18, toBase18
from util.constants import BROWNIE_PROJECT as B
from util.test import conftest

accounts = brownie.network.accounts
account0 = accounts[0]

CHAINID = 0
ADDRESS_FILE = chainlist.chainIdToAddressFile(CHAINID)

@enforce_types
def test_recordDeployedContracts():
    recordDeployedContracts(ADDRESS_FILE, CHAINID)
    assert oceanutil.OCEANtoken()
    assert isinstance(oceanutil.OCEAN_address(), str)
    assert oceanutil.ERC721Template()
    assert oceanutil.ERC20Template()
    assert oceanutil.PoolTemplate()
    assert oceanutil.factoryRouter()
    assert oceanutil.Staking()
    assert oceanutil.ERC721Factory()
    
@enforce_types
def test_OCEANtoken():
    recordDeployedContracts(ADDRESS_FILE, CHAINID)
    OCEAN = OCEANtoken()
    assert OCEAN.symbol().lower() == "ocean"

@enforce_types
def test_createDataNFT():
    recordDeployedContracts(ADDRESS_FILE, CHAINID)
    data_NFT = createDataNFT("nft_name", "nft_symbol", account0)
    assert data_NFT.name() == "nft_name"
    assert data_NFT.symbol() == "nft_symbol"
    
@enforce_types
def test_createDatatokenFromDataNFT():
    recordDeployedContracts(ADDRESS_FILE, CHAINID)
    data_NFT = createDataNFT("foo", "foo", account0)
    DT = createDatatokenFromDataNFT(
        "dt_name", "dt_symbol", data_NFT, account0)
    assert DT.name() == "dt_name"
    assert DT.symbol() == "dt_symbol"

@enforce_types
def test_createBPoolFromDatatoken():
    recordDeployedContracts(ADDRESS_FILE, CHAINID)
    data_NFT = createDataNFT("foo", "foo", account0)
    DT = createDatatokenFromDataNFT("foo", "foo", data_NFT, account0)
    pool = createBPoolFromDatatoken(DT, account0)


@enforce_types
def test_calcDID():
    nft_addr = accounts[3].address #use a random but valid eth address
    did = calcDID(nft_addr, CHAINID)
    assert did[:7] == "did:op:"
    assert len(did) == 71
    
