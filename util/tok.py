# This is a class to help manage a token tuple (chainID, address, symbol)
# E.g. for approved tokens

from typing import Union

from enforce_typing import enforce_types


@enforce_types
class Tok:
    def __init__(self, chainID: int, address: str, symbol: str):
        assert address[:2] == "0x", address
        assert address == address.lower(), address
        assert symbol == symbol.upper(), symbol

        self.chainID = chainID
        self.address = address
        self.symbol = symbol


class TokSet:
    def __init__(self, tups=None):
        """tups - list of (chainID, address, symbol). Will set to [] if None"""
        tups = tups or []
        self.toks = set()
        for (chainID, address, symbol) in tups:
            self.add(chainID, address, symbol)

    def add(self, chainID: int, address: str, symbol: str):
        """
        Add another Tok to this set.
        For a given chain: both address & symbol must be unique.
        """
        assert not self.hasAddress(chainID, address), (chainID, address)
        assert not self.hasSymbol(chainID, symbol), (chainID, symbol)
        tok = Tok(chainID, address, symbol)
        self.toks.add(tok)

    def hasChain(self, chainID: int) -> bool:
        """Are there any tokens at this chainID?"""
        for tok in self.toks:
            if tok.chainID == chainID:
                return True
        return False

    def hasAddress(self, chainID: int, address: str) -> bool:
        """Is there a token at this chainID & address?"""
        tok = self.tokAtAddress(chainID, address)
        return tok is not None

    def hasSymbol(self, chainID: int, symbol: str) -> bool:
        """Is there a token at this chainID & address?"""
        tok = self.tokAtSymbol(chainID, symbol)
        return tok is not None

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
        assert address == address.lower(), address
        assert address[:2] == "0x", address
        for tok in self.toks:
            if tok.chainID == chainID and tok.address == address:
                return tok
        return None

    def tokAtSymbol(self, chainID: int, symbol: str) -> Union[Tok, None]:
        """Returns Tok if there's a token, otherwise returns None"""
        assert symbol == symbol.upper(), symbol
        for tok in self.toks:
            if tok.chainID == chainID and tok.symbol == symbol:
                return tok
        return None

    def exportTokenAddrs(self) -> dict:
        """
        @description -- export in the format used for approved_token_addrs
        @return -- dict of [chainID] : list_of_addr.
        """
        d: dict = {}
        for tok in self.toks:
            if tok.chainID not in d:
                d[tok.chainID] = []
            d[tok.chainID].append(tok.address)
        return d
