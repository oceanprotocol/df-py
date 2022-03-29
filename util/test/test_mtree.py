import brownie
from hexbytes import HexBytes
import pytest

from util.mtree import LeafNode, InternalNode
from util.base18 import fromBase18, toBase18

accounts = brownie.network.accounts

def test_leaf():
    node = _leaf0()
    assert node.solidityKeccak() == HexBytes('0xb99e933b3798d061dbc97519d2fafff7f95663d6183fa8006ebd07456718965c')

def test_0_children():
    with pytest.raises(AssertionError):
        node = InternalNode(left=None, right=None)

def test_1_child_left():
    node = InternalNode(left=_leaf0(), right=None)
    assert node.solidityKeccak() == HexBytes('0xf190a59b3c449b5da10d6693c771e3bd93ef3131a2c12074e39630ac2d04ef14')
    
def test_1_child_right():
    node = InternalNode(left=None, right=_leaf1())
    assert node.solidityKeccak() == HexBytes('0xd57824657082cee1a10369e7c474596a961dfd9124e08cdc27b29d666d4d3136')

def test_2_children():
    node = InternalNode(left=_leaf0(), right=_leaf1())
    assert node.solidityKeccak() == HexBytes('0x0b7e0fe657dbf72ff3c532791836d7a01d57bcc7d55af5d594e48da0f0f36ef2')
    

def _leaf0():
    return LeafNode(accounts[0].address, toBase18(0.1))

def _leaf1():
    return LeafNode(accounts[1].address, toBase18(0.1))
    



