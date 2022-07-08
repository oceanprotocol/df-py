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
def stakesToUsd(
    stakes: dict,
    symbols: Dict[int, Dict[str, str]],
    rates: Dict[str, float],
) -> dict:
    """
    @description
      Converts stake values to be USD-denominated.

    @arguments
      stakes - dict of [chainID][basetoken_addr][pool_addr][LP_addr] : stake
      symbols -- dict of [chainID][basetoken_addr] : basetoken_symbol
      rates - dict of [basetoken_symbol] : USD_price

    @return
      stakes_USD -- dict of [chainID][pool_addr][LP_addr] : stake_USD
    """
    cleancase.assertStakes(stakes)
    cleancase.assertRates(rates)
    addr_rates = ratesToAddrRates(
        rates, symbols
    )  # dict of [chainID][basetoken_addr] : USD_price

    stakes_USD: dict = {}
    for chainID in stakes:
        if chainID not in addr_rates:
            continue

        stakes_USD[chainID] = {}
        for basetoken_addr in stakes[chainID]:
            if basetoken_addr not in addr_rates[chainID]:
                continue
            rate = addr_rates[chainID][basetoken_addr]

            if basetoken_addr not in stakes[chainID]:
                continue
            for pool_addr in stakes[chainID][basetoken_addr]:
                if pool_addr not in stakes_USD[chainID]:
                    stakes_USD[chainID][pool_addr] = {}
                for LP_addr, stake in stakes[chainID][basetoken_addr][
                    pool_addr
                ].items():
                    stakes_USD[chainID][pool_addr][LP_addr] = stake * rate

    cleancase.assertStakesUsd(stakes_USD)
    return stakes_USD


@enforce_types
def poolvolsToUsd(
    poolvols: dict,
    symbols: Dict[int, Dict[str, str]],
    rates: Dict[str, float],
) -> dict:
    """
    @description
      For a given chain, converts volume values to be USD-denominated.

    @arguments
      poolvols -- dict of [chainID][basetoken_address][pool_addr] : vol
      symbols -- dict of [chainID][basetoken_addr] : basetoken_symbol
      rates - dict of [basetoken_symbol] : USD_price

    @return
      poolvols_USD -- dict of [chainID][pool_addr] : vol_USD
    """
    cleancase.assertPoolvols(poolvols)
    cleancase.assertRates(rates)
    addr_rates = ratesToAddrRates(
        rates, symbols
    )  # dict of [chainID][basetoken_addr] : USD_price

    poolvols_USD: dict = {}
    for chainID in poolvols:
        if chainID not in addr_rates:
            continue

        poolvols_USD[chainID] = {}
        for basetoken_addr in poolvols[chainID]:
            if basetoken_addr not in addr_rates[chainID]:
                continue
            rate = addr_rates[chainID][basetoken_addr]

            if basetoken_addr not in poolvols[chainID]:
                continue
            for pool_addr, vol in poolvols[chainID][basetoken_addr].items():
                poolvols_USD[chainID][pool_addr] = vol * rate

    cleancase.assertPoolvolsUsd(poolvols_USD)
    return poolvols_USD
