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
    oceanutil.recordDeployedContracts(ADDRESS_FILE, "development")
    OCEAN = oceanutil.OCEANtoken()
    assert OCEAN.symbol().lower() == "ocean"

def test_createDataNFT(ADDRESS_FILE):
    oceanutil.recordDeployedContracts(ADDRESS_FILE, "development")
    data_NFT = oceanutil.createDataNFT("fooname", "foosymbol", account1)
