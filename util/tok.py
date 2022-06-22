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
        
        
