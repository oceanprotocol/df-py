
from brownie.network import accounts
from enforce_typing import enforce_types
from ocean_lib.models.data_nft import DataNFTArguments

from util.base18 import toBase18, fromBase18


@enforce_types
def test_createDataNFT(data_nft_factory):
    data_NFT = data_nft_factory.create(DataNFTArguments('1','1'), accounts[0])
    assert data_NFT.name() == '1'

    
@enforce_types
def test_OCEAN_fixtures(OCEAN, OCEAN_address):
    assert OCEAN.symbol() == "OCEAN"
    assert OCEAN.address == OCEAN_address


@enforce_types
def test_account0_has_OCEAN(OCEAN):
    assert OCEAN.balanceOf(accounts[0]) > 0
