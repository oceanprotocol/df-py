from enforce_typing import enforce_types
from ocean_lib.models.arguments import DataNFTArguments

from util.base18 import toBase18, fromBase18


@enforce_types
def test_createDataNFT(ocean, alice):
    data_NFT = ocean.data_nft_factory.create(DataNFTArguments('1','1'), alice)
    assert data_NFT.name() == '1'


@enforce_types
def test_data_NFT_fixture(data_NFT):
    assert isinstance(data_NFT.name(), str)


@enforce_types
def test_DT_fixture(DT):
    assert isinstance(DT.name(), str)

    
@enforce_types
def test_OCEAN_fixtures(OCEAN, OCEAN_address):
    assert OCEAN.symbol() == "OCEAN"
    assert OCEAN.address == OCEAN_address


@enforce_types
def test_alice_has_OCEAN(OCEAN, alice):
    assert OCEAN.balanceOf(alice) > 0
