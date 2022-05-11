import brownie
from enforce_typing import enforce_types

from util.oceanutil import recordDeployedContracts, OCEANtoken
from util.base18 import fromBase18, toBase18
from util.constants import BROWNIE_PROJECT as B

accounts = brownie.network.accounts
a1, a2, a3 = accounts[1].address, accounts[2].address, accounts[3].address

@enforce_types
def test_OCEANtoken(ADDRESS_FILE, tmp_path):
    recordDeployedContracts(ADDRESS_FILE, "development")
    OCEAN = OCEANtoken()
    assert OCEAN.symbol() == "OCEAN"
