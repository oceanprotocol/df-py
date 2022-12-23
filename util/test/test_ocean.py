from enforce_typing import enforce_types

from util.base18 import toBase18, fromBase18


@enforce_types
def test_createDataNFT(ocean, alice):
    from ocean_lib.models.arguments import DataNFTArguments
    args = DataNFTArguments('NFT1', 'NFT1')
    data_NFT = ocean.data_nft_factory.create(args, alice)
    assert data_NFT.name() == 'NFT1'
    

    
@enforce_types
def test_OCEAN_exists(OCEAN, OCEAN_address):
    assert OCEAN.symbol() == "OCEAN"
    assert OCEAN.address == OCEAN_address


@enforce_types
def test_alice_has_OCEAN(OCEAN, alice):
    assert OCEAN.balanceOf(alice) > 0
