from enforce_typing import enforce_types

from df_py.volume import cleancase, csvs
from typing import Tuple


@enforce_types
def allocs_to_stakes(allocs: dict, vebals: dict) -> dict:
    """
    For each % allocated value, multiply it with appropriate balance and return
    the absolute allocated value (="stake").

    @arguments
      allocs - dict of [chainID][nft_addr][LP_addr] : percent_allocation_float
      vebals - dict of [LP_addr] : veOCEAN_float -- total balance per LP

    @return
      stakes - dict of [chainID][nft_addr][LP_addr] : veOCEAN_float - abs alloc
    """

    allocs = cleancase.mod_allocations(allocs)
    vebals = cleancase.mod_vebals(vebals)

    stakes = allocs.copy()  # we'll be changing the values
    for chainID in allocs:
        for nft_addr in allocs[chainID]:
            for LP_addr, perc_alloc in allocs[chainID][nft_addr].items():
                vebal = vebals.get(LP_addr, 0.0)
                stake = perc_alloc * vebal
                stakes[chainID][nft_addr][LP_addr] = stake

    cleancase.assert_stakes(stakes)
    return stakes


@enforce_types
def load_stakes(csv_dir: str) -> Tuple[dict, dict]:
    """
    Loads allocs and vebals, computes stakes from it, and returns stakes.

    @return
      stakes - dict of [chainID][nft_addr][LP_addr] : veOCEAN_float - abs alloc
      locked_amts_per_nft - dict of [chainID][nft_addr][LP_addr] : OCEAN_float - abs alloc
    """
    allocs = csvs.load_allocation_csvs(csv_dir)
    vebals, locked_amts, _ = csvs.load_vebals_csv(csv_dir)
    stakes = allocs_to_stakes(allocs, vebals)
    locked_amts_per_nft = allocs_to_stakes(allocs, locked_amts)
    return stakes, locked_amts_per_nft
