import brownie

from util.base18 import toBase18
from util.constants import BROWNIE_PROJECT as B
from util.oceanutil import CONTRACTS as C
from util import oceanutil

def test1():
    network = brownie.network
    account0 = network.accounts[0]
    
    #connected?
    assert network.is_connected()
    assert network.chain.id == 8996 #development / ganache

    #deploy a simple token
    t = B.Simpletoken.deploy("TEST", "TEST", 18, 100, {'from': account0})
    print(t.symbol())

    #deploy Ocean contracts: OCEAN
    C["Ocean"] = B.Simpletoken.deploy(
        "OCEAN", "OCEAN", 18, toBase18(1.41e9), {'from': account0})
    assert oceanutil.OCEANtoken() is not None #will use C["Ocean"]

    #deploy Ocean contracts: the rest
    C["ERC721Template"] = B.ERC721Template.deploy({'from': account0})
    C["ERC20Template"] = B.ERC20Template.deploy({'from': account0})
    C["PoolTemplate"] = B.BPool.deploy({'from': account0})
    C["Router"] = B.FactoryRouter.deploy(
        account0.address,            # _routerOwner
        C["Ocean"].address,          # _oceanToken
        C["PoolTemplate"].address,   # _bpoolTemplate
        account0.address,            # _opcCollector
        [],                          # _preCreatedPools
        {'from': account0})
    C["Staking"] = B.SideStaking.deploy(
        C["Router"].address,         # _router
        {'from': account0})
    C["ERC721Factory"] = B.ERC721Factory.deploy(
        C["ERC721Template"].address, # _template721
        C["ERC20Template"].address,  # _template
        C["Router"].address,         # _router
        {'from': account0})

    #ensure ADDRESS_FILE (address.json path) is set to what we expect
    
    #update the values in ADDRESS_FILE


