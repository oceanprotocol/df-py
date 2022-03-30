#Merkle Tree, tuned for DF needs

from abc import ABC, abstractmethod
from brownie import web3
import numpy

class AbstractNode(ABC):
    @abstractmethod
    def solidityKeccak(self):
        """
        Like web3.solidityKeccak(abi_types, value):

        Returns the Keccak-256 as it would be computed by the solidity keccak
        function on a packed ABI encoding of the value list contents. The 
        abi_types argument should be a list of solidity type strings which 
        correspond to each of the provided values.

        >>> Web3.solidityKeccak(['uint8[]'], [[97, 98, 99]])
        HexBytes("0x233002c671295529bcc..")

        >>> Web3.solidityKeccak(['address'],
         ["0x49EdDD3769c0712032808D86597B84ac5c2F5614"])
        HexBytes("0x2ff37b5607484cd4eecf6..")

        https://web3py.readthedocs.io/en/stable/web3.main.html
        """
        pass
    
    @abstractmethod
    def verify(self, proof:list, root, leaf):
        """
        Returns True if a `leaf` can be proved to be a part of a Merkle tree
        defined by `root`. For this, a `proof` must be provided, containing
        sibling hashes on the branch from the leaf to the root of the tree. Each
        pair of leaves and each pair of pre-images are assumed to be sorted.

        Note: this is the same interface as MerkleProof.sol::verify() by design.
        """
        pass

class LeafNode(AbstractNode):
    def __init__(self, address:str, amt_OCEAN:float):
        """The 'data' in DF Merkle trees is {address, amt_OCEAN}."""
        self.address:str = address
        self.amt_OCEAN:float = amt_OCEAN
        self._hash = None

    def solidityKeccak(self):
        if self._hash is None:
            abi_types = ["address", "uint256"]
            values = [self.address, toBase18(self.amt_OCEAN)]
            self._hash = web3.solidityKeccak(abi_types, values)
        return self._hash

    def verify(self, proof:list, root, leaf):
        return 

def buildTreeFromDict(rewards:dict):
    """
    @arguments 
      rewards -- dict of [address_str] : amt_OCEAN_float
    @return
      tree --
    """
    rewards_list = _sortedRewardsList(rewards)
    return buildTreeFromList(rewards_list)

def buildTreeFromList(rewards_list):
    """
    @arguments 
      rewards_list -- list of [(address_str, amt_OCEAN_float)]
    @return
      tree -- AbstractTree --
    """
    N = len(rewards_list)
    assert N > 0, "need entries"
    if N == 1:
        address, amt_OCEAN = rewards_list[0]
        return LeafNode(address, amt_OCEAN)
    else:
        left = _buildTreeFromList(rewards_list[:N/2])
        right = _buildTreeFromList(rewards_list[N/2:])
        return InternalNode(left, right)
    
def _sortedRewardsList(rewards_dict:dict):
    """@return -- rewards_list -- list of (address_str, amt_OCEAN_float), 
    sorted from largest amt_OCEAN to smallest."""
    addrs = rewards_dict.keys()
    amts = [rewards_dict[a] for a in addrs]
    I = numpy.argsort(amts, reverse=True)[::-1]
    return [(addrs[i], rewards_dict[addrs[i]]) for i in I]


class InternalNode(AbstractNode):
    def __init__(self, left, right):
        self.left = left
        self.right = right        
        self._hash = None

    def solidityKeccak(self):
        if self._hash is None:
            abi_types, values = [], []
            if self.left is not None:
                abi_types.append("bytes")
                values.append(self.left.solidityKeccak())
            if self.right is not None:
                abi_types.append("bytes")
                values.append(self.right.solidityKeccak())
            self._hash = web3.solidityKeccak(abi_types, values)
        return self._hash

    def verify(self, proof:list, root, leaf):
        raise NotImplementedError()
