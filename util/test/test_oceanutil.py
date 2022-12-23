from enforce_typing import enforce_types

from util.networkutil import DEV_CHAINID
from util import oceanutil

@enforce_types
def test_calcDID():
    nft_addr = "0xdafea492d9c6733ae3d56b7ed1adb60692c98bc5" #random eth addr
    did = oceanutil.calcDID(nft_addr, DEV_CHAINID) 
    assert did[:7] == "did:op:"
    assert len(did) == 71

