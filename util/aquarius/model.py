from enforce_typing import enforce_types

from util import oceanutil


@enforce_types
class SimpleDataNft:
    def __init__(
        self,
        chain_id: int,
        nft_addr: str,
        _symbol: str,
        owner_addr: str,
        is_purgatory: bool = False,
        name: str = "",
    ):
        self.chain_id = chain_id
        self.nft_addr = nft_addr.lower()
        self.symbol = _symbol.upper()
        self.owner_addr = owner_addr.lower()
        self.is_purgatory = is_purgatory
        self.name = name  # can be any mix of upper and lower case
        self.did = oceanutil.calcDID(nft_addr, chain_id)

    def setName(self, name: str):
        self.name = name

    def __eq__(self, x) -> bool:
        return repr(self) == repr(x)

    def __repr__(self) -> str:
        return (
            f"SimpleDataNft("
            f"{self.chain_id}, '{self.nft_addr}', '{self.symbol}', "
            f"'{self.owner_addr}', {self.is_purgatory}, '{self.name}'"
            f")"
        )
