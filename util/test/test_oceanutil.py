import brownie
from enforce_typing import enforce_types

from util import oceanutil
from util.base18 import fromBase18, toBase18
from util.constants import BROWNIE_PROJECT as B

accounts = brownie.network.accounts
account1 = accounts[1]
addr1 = account1.address

@enforce_types
def test_recordDeployedContracts(ADDRESS_FILE):
    oceanutil.recordDeployedContracts(ADDRESS_FILE, "development")
    
@enforce_types
def test_OCEANtoken(ADDRESS_FILE):
    _setup(ADDRESS_FILE)
    OCEAN = oceanutil.OCEANtoken()
    assert OCEAN.symbol().lower() == "ocean"

def test_createDataNFT(ADDRESS_FILE):
    _setup(ADDRESS_FILE)
    data_NFT = oceanutil.createDataNFT("nft_name", "nft_symbol", account1)
    assert data_NFT.name() == "nft_name"
    assert data_NFT.symbol() == "nft_symbol"
    
def test_createDatatokenFromDataNFT(ADDRESS_FILE):
    _setup(ADDRESS_FILE)
    data_NFT = oceanutil.createDataNFT("nft_name", "nft_symbol", account1)
    DT = oceanutil.createDatatokenFromDataNFT(
        "dt_name", "dt_symbol", data_NFT, account1)
    assert DT.name() == "dt_name"
    assert DT.symbol() == "dt_symbol"

def _setup(ADDRESS_FILE):
    oceanutil.recordDeployedContracts(ADDRESS_FILE, "development")
    
