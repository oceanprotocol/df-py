from typing import Dict

from enforce_typing import enforce_types

from util import cleancase
from util.tok import TokSet


@enforce_types
def stakesToUsd(stakes: dict, rates: Dict[str, float], tok_set: TokSet) -> dict:
    """
    @description
      Converts stake values to be USD-denominated.

    @arguments
      stakes - dict of [chainID][basetoken_address][pool_addr][LP_addr] : stake
      rates - dict of [basetoken_symbol] : USD_per_basetoken
      tok_set - TokSet

    @return
      stakes_USD -- dict of [chainID][pool_addr][LP_addr] : stake_USD
    """
    cleancase.assertStakes(stakes)
    cleancase.assertRates(rates)

    stakes_USD: dict = {}
    for chainID in stakes:
        stakes_USD[chainID] = {}
        for base_symb, rate in rates.items():
            if not tok_set.hasSymbol(chainID, base_symb):
                continue
            base_addr = tok_set.getAddress(chainID, base_symb)
            if base_addr not in stakes[chainID]:
                continue
            for pool_addr in stakes[chainID][base_addr].keys():
                stakes_USD[chainID][pool_addr] = {}
                for LP_addr, stake in stakes[chainID][base_addr][pool_addr].items():
                    stakes_USD[chainID][pool_addr][LP_addr] = stake * rate

    cleancase.assertStakesUsd(stakes_USD)
    return stakes_USD


@enforce_types
def poolvolsToUsd(poolvols: dict, rates: Dict[str, float], tok_set: TokSet) -> dict:
    """
    @description
      For a given chain, converts volume values to be USD-denominated.

    @arguments
      poolvols -- dict of [chainID][basetoken_address][pool_addr] : vol
      rates -- dict of [basetoken_symbol] : USD_per_basetoken
      tok_set - TokSet

    @return
      poolvols_USD -- dict of [chainID][pool_addr] : vol_USD
    """
    cleancase.assertPoolvols(poolvols)
    cleancase.assertRates(rates)

    poolvols_USD: dict = {}
    for chainID in poolvols:
        poolvols_USD[chainID] = {}
        for base_symb, rate in rates.items():
            if not tok_set.hasSymbol(chainID, base_symb):
                continue
            base_addr = tok_set.getAddress(chainID, base_symb)
            if base_addr not in poolvols[chainID]:
                continue
            for pool_addr, vol in poolvols[chainID][base_addr].items():
                poolvols_USD[chainID][pool_addr] = vol * rate

    cleancase.assertPoolvolsUsd(poolvols_USD)
    return poolvols_USD
