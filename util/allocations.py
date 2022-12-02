from enforce_typing import enforce_types

from util import cleancase, csvs


@enforce_types
def allocsToStakes(allocs: dict, vebals: dict) -> dict:
    """
    For each % allocated value, multiply it with appropriate balance and return
    the absolute allocated value (="stake").

    @arguments
      allocs - dict of [chainID][nft_addr][LP_addr] : percent_allocation_float
      vebals - dict of [LP_addr] : veOCEAN_float -- total balance per LP

    @return
      stakes - dict of [chainID][nft_addr][LP_addr] : veOCEAN_float - abs alloc
    """

    allocs = cleancase.modAllocations(allocs)
    vebals = cleancase.modVebals(vebals)

    stakes = allocs.copy()  # we'll be changing the values
    for chainID in allocs:
        for nft_addr in allocs[chainID]:
            for LP_addr, perc_alloc in allocs[chainID][nft_addr].items():
                vebal = vebals.get(LP_addr, 0.0)
                stake = perc_alloc * vebal
                stakes[chainID][nft_addr][LP_addr] = stake

    cleancase.assertStakes(stakes)
    return stakes


def loadStakes(csv_dir: str) -> dict:
    """
    Loads allocs and vebals, computes stakes from it, and returns stakes.

    @return
      stakes - dict of [chainID][nft_addr][LP_addr] : veOCEAN_float - abs alloc
    """
    allocs = csvs.loadAllocationCsvs(csv_dir)
    vebals, _, _ = csvs.loadVebalsCsv(csv_dir)
    stakes = allocsToStakes(allocs, vebals)
    return stakes
