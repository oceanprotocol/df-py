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
      For each rate, assign it the appropriate chain_id and token_addr

    @arguments
      rates - dict of [token_symbol] : USD_price
      symbols -- dict of [chainID][token_addr] : token_symbol

    @return
      addr_rates -- dict of [chainID][token_addr] : USD_price
    """
    addr_rates: dict = {}
    for chain_id in symbols:
        addr_rates[chain_id] = {}
        for token_addr, token_symbol in symbols[chain_id].items():
            if token_symbol in rates:
                addr_rates[chain_id][token_addr] = rates[token_symbol]
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
    for chain_id in _CHAINID_TO_ADDRS:
        token_addr = _CHAINID_TO_ADDRS[chain_id]
        token_symbol = _CHAINID_TO_NATIVE_TOKEN[chain_id]

        if chain_id not in symbols:
            symbols[chain_id] = {}

        symbols[chain_id][token_addr] = token_symbol

    addr_rates = rates_to_addr_rates(
        rates, symbols
    )  # dict of [chain_id][basetoken_addr] : USD_price

    nftvols_USD: dict = {}
    for chain_id in nftvols:
        if chain_id not in addr_rates:
            continue

        nftvols_USD[chain_id] = {}
        for basetoken_addr in nftvols[chain_id]:
            if basetoken_addr not in addr_rates[chain_id]:
                continue
            rate = addr_rates[chain_id][basetoken_addr]

            if basetoken_addr not in nftvols[chain_id]:
                continue
            for nft_addr, vol in nftvols[chain_id][basetoken_addr].items():
                nftvols_USD[chain_id][nft_addr] = vol * rate
    return nftvols_USD
