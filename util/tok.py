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
    def __init__(self):
        self.toks = set()

    def add(self, tok: Tok):
        """
        Add another Tok to this set. 
        For a given chain: both address & symbol must be unique.
        """
        assert not self.hasAddress(tok.chainID, tok.address)
        assert not self.hasSymbol(tok.chainID, tok.symbol)
        self.toks.add(tok)

    def hasAddress(self, chainID: int, address: str) -> bool:
        """Is there a token at this chainID & address?"""
        tok = self.tokAtAddress(chainID, address)
        return (tok is not None)

    def hasSymbol(self, chainID: int, symbol: str) -> bool:
        """Is there a token at this chainID & address?"""
        tok = self.tokAtSymbol(chainID, symbol)
        return (tok is not None)

    def getSymbol(self, chainID: int, address: str) -> str:
        """Returns Tok's symbol if there's a token, otherwise raises an error"""
        tok = self.tokAtAddress(chainID, address)
        assert tok is not None
        return tok.symbol

    def getAddress(self, chainID: int, symbol: str) -> str:
        """Returns Tok's address if there's a token, otherwise raises an error"""
        tok = self.tokAtSymbol(chainID, symbol)
        assert tok is not None
        return tok.address

    def tokAtAddress(self, chainID: int, address: str) -> Union[Tok, None]:
        """Returns Tok if there's a token, otherwise returns None"""
        assert address == address.lower()
        assert address[:2] == "0x"
        for tok in self.toks:
            if tok.chainID == chainID and tok.address == address:
                return tok
        return None

    def tokAtSymbol(self, chainID: int, symbol: str) -> Union[Tok, None]:
        """Returns Tok if there's a token, otherwise returns None"""
        assert symbol == symbol.upper()
        for tok in self.toks:
            if tok.chainID == chainID and tok.symbol == symbol:
                return tok
        return None
        

