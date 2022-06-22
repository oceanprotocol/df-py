# This is a class to help manage a token tuple (chainID, address, symbol)
# E.g. for approved tokens

from typing import Set, Union

from enforce_typing import enforce_types

@enforce_types
class Tok:
    def __init__(self, chainID : int, address: str, symbol : str):
        assert address[:2] == "0x"
        assert address == address.lower()
        assert symbol == symbol.upper()
        
        self.chainID = chainID
        self.address = address
        self.symbol = symbol
        
class TokSet:
    def __init__(self, toks: Set[Tok]):
        self.toks = toks

    def hasAddress(self, chainID: int, address: str) -> bool:
        """Is there a token at this chainID & address?"""
        tok = self.tokAtAddress(chainID, address)
        return (tok is not None)

    def symbol(self, chainID: int, address: str) -> str:
        """Returns Tok's symbol if there's a token, otherwise raises an error"""
        tok = self.tokAtAddress(chainID, address)
        assert tok is not None
        return tok.symbol

    def tokAtAddress(self, chainID: int, address: str) -> Union[Tok, None]:
        """Returns Tok if there's a token, otherwise returns None"""
        assert address == address.lower()
        for tok in self.toks:
            if tok.chainID == chainID and tok.address == address:
                return tok
        return None
        

