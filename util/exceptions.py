#adapted from https://github.com/raiden-network/raiden/blob/e43ebbb8c09407d9793e50b1005bfdb67c267b4a/raiden/exceptions.py

class DfError(Exception):
    """ Base exception, used to catch all raiden related exceptions. """
    pass

# Exceptions raised due to programming errors

class HashLengthNot32(DfError):
    """ Raised if the length of the provided element is not 32 bytes in length,
    a keccak hash is required to include the element in the merkle tree.
    """
    pass
