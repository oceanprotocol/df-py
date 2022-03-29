from util.mtree import LeafNode, InternalNode
from util.base18 import fromBase18, toBase18

def test_LeafNode():
    address = "0x123"
    amt_OCEAN = toBase18(0.1)
    node = LeafNode(address, amt_OCEAN)
    assert node.solidityKeccak() == "foo"
