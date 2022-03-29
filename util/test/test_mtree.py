import brownie
from hexbytes import HexBytes

from util.mtree import LeafNode, InternalNode
from util.base18 import fromBase18, toBase18

accounts = brownie.network.accounts

def test_LeafNode():
    address = accounts[0].address
    amt_OCEAN = toBase18(0.1)
    node = LeafNode(address, amt_OCEAN)
    assert node.solidityKeccak() == HexBytes('0xb99e933b3798d061dbc97519d2fafff7f95663d6183fa8006ebd07456718965c')
