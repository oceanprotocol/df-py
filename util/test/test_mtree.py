import brownie
from hexbytes import HexBytes
import pytest

from util.mtree import LeafNode, InternalNode
from util.base18 import fromBase18, toBase18

accounts = brownie.network.accounts

def test_leaf():
    node = _leaf(0)
    assert node.solidityKeccak() == HexBytes('0xb99e933b3798d061dbc97519d2fafff7f95663d6183fa8006ebd07456718965c')

def test_0_children():
    with pytest.raises(AssertionError):
        node = InternalNode(left=None, right=None)

def test_1level_1child_left():
    node = InternalNode(left=_leaf(0), right=None)
    assert node.solidityKeccak() == HexBytes('0xf190a59b3c449b5da10d6693c771e3bd93ef3131a2c12074e39630ac2d04ef14')
    
def test_1level_1child_right():
    node = InternalNode(left=None, right=_leaf(1))
    assert node.solidityKeccak() == HexBytes('0xd57824657082cee1a10369e7c474596a961dfd9124e08cdc27b29d666d4d3136')

def test_1level_2children():
    node = InternalNode(left=_leaf(0), right=_leaf(1))
    assert node.solidityKeccak() == HexBytes('0x0b7e0fe657dbf72ff3c532791836d7a01d57bcc7d55af5d594e48da0f0f36ef2')

def test_2levels():
    A, B, C, D = _leaf(0), _leaf(1), _leaf(2), _leaf(3)
    AB, CD = InternalNode(A,B), InternalNode(C,D)
    ABCD = InternalNode(AB, CD)
    assert ABCD.left.right == B
    assert ABCD.solidityKeccak() == HexBytes('0x8d0d89043c4c76cc1d2d858ff189d248ab1094a0fac494647fa4d0640cc18334')
    
def _leaf(i:int):
    return LeafNode(accounts[i].address, toBase18(0.1))



