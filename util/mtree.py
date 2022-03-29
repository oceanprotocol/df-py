#Merkle Tree, tuned for DF needs

from abc import ABC, abstractmethod
from brownie import web3

class AbstractNode(ABC):
    @abstractmethod
    def solidityKeccak(self):
        pass

class LeafNode(AbstractNode):
    def __init__(self, address:str, amt_OCEAN:int):
        self.address:str = address
        self.amt_OCEAN:int = amt_OCEAN
        self._hash = None

    def solidityKeccak(self):
        if self._hash is None:
            abi_types = ["address", "uint256"]
            values = [self.address, self.amt_OCEAN]
            self._hash = web3.solidityKeccak(abi_types, values)
        return self._hash

class InternalNode(AbstractNode):
    def __init__(self, left:AbstractNode, right:AbstractNode):
        assert left is not None or right is not None
        self.left:AbstractNode = left
        self.right:AbstractNode = right
        self._hash = None

    def solidityKeccak(self):
        if self._hash is None:
            abi_types, values = [], []
            if self.left is not None:
                abi_types.append("bytes")
                values.append(self.left.solidityKeccak)
            if self.right is not None:
                abi_types.append("bytes")
                values.append(self.right.solidityKeccak)
            self._hash = web3.solidityKeccak(abi_types, values)
        return self._hash




# web3.solidityKeccak(abi_types, value):
#   Returns the Keccak-256 as it would be computed by the solidity keccak
#   function on a packed ABI encoding of the value list contents. The abi_types
#   argument should be a list of solidity type strings which correspond to
#   each of the provided values.
#
#   >>> Web3.solidityKeccak(['uint8[]'], [[97, 98, 99]])
#   HexBytes("0x233002c671295529bcc..")
#
#   >>> Web3.solidityKeccak(['address'],
#    ["0x49EdDD3769c0712032808D86597B84ac5c2F5614"])
#   HexBytes("0x2ff37b5607484cd4eecf6..")
#
#   https://web3py.readthedocs.io/en/stable/web3.main.html
