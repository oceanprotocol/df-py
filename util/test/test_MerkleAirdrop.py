import brownie

from util import oceanutil
from util.constants import BROWNIE_PROJECT062 as B

accounts = brownie.network.accounts
chain = brownie.network.chain

def test_1(ADDRESS_FILE):
    oceanutil.recordDeployedContracts(ADDRESS_FILE, "development")
    OCEAN = oceanutil.OCEANtoken()
    
    a = B.MerkleAirdrop.deploy(
        OCEAN.address,
        {"from": accounts[0]},
    )
