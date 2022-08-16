from typing import Dict

from enforce_typing import enforce_types

from util import cleancase


@enforce_types
def ratesToAddrRates(
    rates: Dict[str, float],
    symbols: Dict[int, Dict[str, str]],
) -> dict:
    """
    @description
      Converts stake values to be USD-denominated.

    @arguments
      rates - dict of [token_symbol] : USD_price
      symbols -- dict of [chainID][token_addr] : token_symbol

    @return
      addr_rates -- dict of [chainID][token_addr] : USD_price
    """
    addr_rates: dict = {}
    for chainID in symbols:
        addr_rates[chainID] = {}
        for token_addr, token_symbol in symbols[chainID].items():
            if token_symbol in rates:
                addr_rates[chainID][token_addr] = rates[token_symbol]
    return addr_rates


@enforce_types
def nftvolsToUsd(
    nftvols: dict,
    symbols: Dict[int, Dict[str, str]],
    rates: Dict[str, float],
) -> dict:
    """
    @description
      For a given chain, converts volume values to be USD-denominated.

    @arguments
      nftvols -- dict of [chainID][basetoken_address][pool_addr] : vol
      symbols -- dict of [chainID][basetoken_addr] : basetoken_symbol
      rates - dict of [basetoken_symbol] : USD_price

    @return
      nftvols_USD -- dict of [chainID][pool_addr] : vol_USD
    """
    cleancase.assertNFTvols(nftvols)
    cleancase.assertRates(rates)
    addr_rates = ratesToAddrRates(
        rates, symbols
    )  # dict of [chainID][basetoken_addr] : USD_price

    nftvols_USD: dict = {}
    for chainID in nftvols:
        if chainID not in addr_rates:
            continue

        nftvols_USD[chainID] = {}
        for basetoken_addr in nftvols[chainID]:
            if basetoken_addr not in addr_rates[chainID]:
                continue
            rate = addr_rates[chainID][basetoken_addr]

            if basetoken_addr not in nftvols[chainID]:
                continue
            for nft_addr, vol in nftvols[chainID][basetoken_addr].items():
                nftvols_USD[chainID][nft_addr] = vol * rate

    cleancase.assertnftvolsUsd(nftvols_USD)
    return nftvols_USD
