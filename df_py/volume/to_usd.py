from typing import Dict

from enforce_typing import enforce_types

from df_py.util.networkutil import _CHAINID_TO_ADDRS, _CHAINID_TO_NATIVE_TOKEN
from df_py.volume import cleancase


@enforce_types
def rates_to_addr_rates(
    rates: Dict[str, float],
    symbols: Dict[int, Dict[str, str]],
) -> dict:
    """
    @description
      For each rate, assign it the appropriate chainID and token_addr

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
def nft_vols_to_usd(
    nftvols: Dict[int, Dict[str, Dict[str, float]]],
    symbols: Dict[int, Dict[str, str]],
    rates: Dict[str, float],
) -> Dict[int, Dict[str, str]]:
    """
    @description
      For a given chain, converts volume values to be USD-denominated.

    @arguments
      nftvols -- dict of [chainID][basetoken_address][nft_addr] : vol
      symbols -- dict of [chainID][basetoken_addr] : basetoken_symbol
      rates - dict of [basetoken_symbol] : USD_price

    @return
      nftvols_USD -- dict of [chainID][nft_addr] : vol_USD
    """
    cleancase.assert_nft_vols(nftvols)
    cleancase.assert_rates(rates)

    # Add native token rates
    for chainID in _CHAINID_TO_ADDRS:
        token_addr = _CHAINID_TO_ADDRS[chainID]
        token_symbol = _CHAINID_TO_NATIVE_TOKEN[chainID]

        if chainID not in symbols:
            symbols[chainID] = {}

        symbols[chainID][token_addr] = token_symbol

    addr_rates = rates_to_addr_rates(
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
    return nftvols_USD
