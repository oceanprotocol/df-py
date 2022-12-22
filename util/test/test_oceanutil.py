import brownie
from enforce_typing import enforce_types

from util.networkutil import DEV_CHAINID

@enforce_types
def test_createDataset(ocean, alice):
    name = "Branin dataset"
    url = "https://raw.githubusercontent.com/trentmc/branin/main/branin.arff"
    (data_nft, datatoken, ddo) = ocean.assets.create_url_asset(name, url, alice)
    assert data_NFT.name() == name

    
@enforce_types
def test_OCEAN_exists(OCEAN, OCEAN_address):
    assert OCEAN.symbol() == "OCEAN"
    assert OCEAN.address == OCEAN_address


@enforce_types
def test_alice_has_OCEAN(OCEAN, alice):
    assert OCEAN.balanceOf(alice) > 0


@enforce_types
def test_calcDID():
    nft_addr = "0xdafea492d9c6733ae3d56b7ed1adb60692c98bc5" #random eth addr
    did = oceanutil.calcDID(nft_addr, DEV_CHAINID) 
    assert did[:7] == "did:op:"
    assert len(did) == 71

