from enforce_typing import enforce_types


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
