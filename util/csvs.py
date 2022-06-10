import csv
import glob
import os
import re
from typing import Any, Dict, List
from enforce_typing import enforce_types

from util import constants, oceanutil


# ========================================================================
# stakes csvs


@enforce_types
def saveStakesCsv(stakes_at_chain: dict, csv_dir: str, chainID: int):
    """
    @description
      Save the stakes csv for this chain

    @arguments
      stakes_at_chain -- dict of [basetoken_address][pool_addr][LP_addr] : stake_amt
      csv_dir -- directory that holds csv files
      chainID -- which network
    """
    assert os.path.exists(csv_dir), csv_dir
    csv_file = stakesCsvFilename(csv_dir, chainID)
    assert not os.path.exists(csv_file), csv_file
    S = stakes_at_chain
    with open(csv_file, "w") as f:
        writer = csv.writer(f)
        row = ["chainID", "basetoken", "pool_addr", "LP_addr", "stake_amt"]
        writer.writerow(row)
        for basetoken in S.keys():
            for pool_addr in S[basetoken].keys():
                for LP_addr, stake in S[basetoken][pool_addr].items():
                    row = [str(chainID), basetoken, pool_addr, LP_addr, stake]
                    writer.writerow(row)
    print(f"Created {csv_file}")


@enforce_types
def loadStakesCsvs(csv_dir: str):
    """
    @description
      Load all stakes csvs (across all chains); return result as a single dict

    @return
      stakes -- dict of [chainID][basetoken_address][pool_addr][LP_addr] : stake_amt
    """
    csv_files = stakesCsvFilenames(csv_dir)
    stakes = {}
    for csv_file in csv_files:
        chainID = chainIDforStakeCsv(csv_file)
        stakes[chainID] = loadStakesCsv(csv_dir, chainID)
    return stakes


@enforce_types
def loadStakesCsv(csv_dir: str, chainID: int):
    """
    @description
      Load stakes csv for this chainID

    @return
      stakes_at_chain -- dict of [basetoken_address][pool_addr][LP_addr] : stake_amt
    """
    csv_file = stakesCsvFilename(csv_dir, chainID)
    S: Dict[str, Dict[str, Dict[str, float]]] = {}  # ie stakes_at_chain
    with open(csv_file, "r") as f:
        reader = csv.reader(f)
        for row_i, row in enumerate(reader):
            if row_i == 0:  # header
                assert row == [
                    "chainID",
                    "basetoken",
                    "pool_addr",
                    "LP_addr",
                    "stake_amt",
                ]
                continue

            chainID2 = int(row[0])
            basetoken = row[1].upper()
            pool_addr = row[2].lower()
            LP_addr = row[3].lower()
            stake_amt = float(row[4])
            assert chainID2 == chainID, "csv had data from different chain"

            if basetoken not in S:
                S[basetoken] = {}
            if pool_addr not in S[basetoken]:
                S[basetoken][pool_addr] = {}
            assert LP_addr not in S[basetoken][pool_addr], "duplicate found"
            S[basetoken][pool_addr][LP_addr] = stake_amt
    print(f"Loaded {csv_file}")

    return S


@enforce_types
def stakesCsvFilenames(csv_dir: str) -> List[str]:
    """Returns a list of stakes filenames in this directory"""
    return glob.glob(os.path.join(csv_dir, "stakes*.csv"))


@enforce_types
def stakesCsvFilename(csv_dir: str, chainID: int) -> str:
    """Returns the stakes filename for a given chainID"""
    return os.path.join(csv_dir, f"stakes-chain{chainID}.csv")


@enforce_types
def chainIDforStakeCsv(filename) -> int:
    """Returns chainID for a given stakes csv filename"""
    return _lastInt(filename)


# ========================================================================
# poolvols csvs


@enforce_types
def savePoolvolsCsv(poolvols_at_chain: dict, csv_dir: str, chainID: int):
    """
    @description
      Save the poolvols csv for this chain

    @arguments
      poolvols_at_chain -- dict of [basetoken_address][pool_addr] : vol_amt
      csv_dir -- directory that holds csv files
      chainID -- which network
    """
    assert os.path.exists(csv_dir), csv_dir
    csv_file = poolvolsCsvFilename(csv_dir, chainID)
    assert not os.path.exists(csv_file), csv_file
    V = poolvols_at_chain
    with open(csv_file, "w") as f:
        writer = csv.writer(f)
        writer.writerow(["chainID", "basetoken", "pool_addr", "vol_amt"])
        for basetoken in V.keys():
            for pool_addr, vol in V[basetoken].items():
                writer.writerow([chainID, basetoken, pool_addr, vol])
    print(f"Created {csv_file}")


@enforce_types
def loadPoolvolsCsvs(csv_dir: str):
    """
    @description
      Load all poolvols csvs (across all chains); return result as single dict

    @return
      poolvols -- dict of [chainID][basetoken_address][pool_addr] : vol_amt
    """
    csv_files = poolvolsCsvFilenames(csv_dir)
    poolvols = {}
    for csv_file in csv_files:
        chainID = chainIDforPoolvolsCsv(csv_file)
        poolvols[chainID] = loadPoolvolsCsv(csv_dir, chainID)
    return poolvols


@enforce_types
def loadPoolvolsCsv(csv_dir: str, chainID: int):
    """
    @description
      Load poolvols for this chainID

    @return
      poolvols_at_chain -- dict of [basetoken_address][pool_addr] : vol_amt
    """
    csv_file = poolvolsCsvFilename(csv_dir, chainID)
    V: Dict[str, Dict[str, float]] = {}  # ie poolvols_at_chain
    with open(csv_file, "r") as f:
        reader = csv.reader(f)
        for row_i, row in enumerate(reader):
            if row_i == 0:  # header
                assert row == ["chainID", "basetoken", "pool_addr", "vol_amt"]
                continue
            chainID2 = int(row[0])
            basetoken = row[1].upper()
            pool_addr = row[2].lower()
            vol_amt = float(row[3])
            assert chainID2 == chainID, "csv had data from different chain"

            if basetoken not in V:
                V[basetoken] = {}
            assert pool_addr not in V[basetoken], "duplicate found"
            V[basetoken][pool_addr] = vol_amt
    print(f"Loaded {csv_file}")

    return V


@enforce_types
def poolvolsCsvFilenames(csv_dir: str) -> List[str]:
    """Returns a list of poolvols filenames in this directory"""
    return glob.glob(os.path.join(csv_dir, "poolvols*.csv"))


@enforce_types
def poolvolsCsvFilename(csv_dir: str, chainID: int) -> str:
    """Returns the poolvols filename for a given chainID"""
    return os.path.join(csv_dir, f"poolvols-{chainID}.csv")


@enforce_types
def chainIDforPoolvolsCsv(filename) -> int:
    """Returns chainID for a given poolvols csv filename"""
    return _lastInt(filename)


# ========================================================================
# poolinfo csvs


@enforce_types
def savePoolinfoCsv(
    pools_at_chain: list,
    stakes_at_chain: dict,
    poolvols_at_chain: dict,
    csv_dir: str,
    chainID: int,
):
    """
    @description
      Save detailed info for this pool.

    @arguments
      pools_at_chain -- list of SimplePool
      stakes_at_chain -- dict of [basetoken_address][pool_addr][LP_addr] : stake_amt
      poolvols_at_chain -- dict of [basetoken_address][pool_addr] : vol_amt
      csv_dir -- directory that holds csv files
      chainID -- which network
    """
    assert os.path.exists(csv_dir), f"{csv_dir} should exist"
    csv_file = poolinfoCsvFilename(csv_dir, chainID)
    assert not os.path.exists(csv_file), f"{csv_file} shouldn't exist"

    pools_by_addr = {pool.addr: pool for pool in pools_at_chain}

    with open(csv_file, "w") as f:
        writer = csv.writer(f)
        writer.writerow(
            [
                "chainID",
                "basetoken",
                "pool_addr",
                "vol_amt",
                "stake_amt",
                "nft_addr",
                "DT_addr",
                "DT_symbol",
                "basetoken_addr",
                "did",
                "url",
            ]
        )

        for basetoken in stakes_at_chain:
            for pool_addr in pools_by_addr:
                if pool_addr not in stakes_at_chain[basetoken]:
                    continue

                p = pools_by_addr[pool_addr]
                did = oceanutil.calcDID(p.nft_addr, chainID)
                url = constants.MARKET_ASSET_BASE_URL + did

                stake_amt = sum(stakes_at_chain[basetoken][pool_addr].values())

                vol = 0
                if basetoken in poolvols_at_chain:
                    if pool_addr in poolvols_at_chain[basetoken]:
                        vol = poolvols_at_chain[basetoken][pool_addr]

                row = [
                    chainID,
                    basetoken,
                    pool_addr,
                    vol,
                    stake_amt,
                    p.nft_addr,
                    p.DT_addr,
                    p.DT_symbol,
                    p.basetoken_addr,
                    did,
                    url,
                ]
                writer.writerow(row)

    print(f"Created {csv_file}")


@enforce_types
def poolinfoCsvFilename(csv_dir: str, chainID: int) -> str:
    """Returns the poolinfo filename for a given chainID"""
    return os.path.join(csv_dir, f"poolinfo-{chainID}.csv")


# ========================================================================
# exchange rate csvs


@enforce_types
def saveRateCsv(token_symbol: str, rate: float, csv_dir: str):
    """
    @description
      Save a csv file for an exchange rate.

    @arguments
      token_symbol -- str -- e.g. "OCEAN", "H2O"
      rate -- float -- $/token, e.g. 0.86
      csv_dir -- directory holding csvs
    """
    token_symbol = token_symbol.upper()
    csv_file = rateCsvFilename(token_symbol, csv_dir)
    assert not os.path.exists(csv_file), f"{csv_file} can't already exist"
    with open(csv_file, "w") as f:
        writer = csv.writer(f)
        writer.writerow(["token", "rate"])
        writer.writerow([token_symbol, str(rate)])
    print(f"Created {csv_file}")


@enforce_types
def loadRateCsvs(csv_dir: str):
    """
    @description
      Load all exchange rate csvs, and return result as a single dict

    @return
      rates -- dict of [token_sym] : rate
    """
    csv_files = rateCsvFilenames(csv_dir)
    rates = {}
    for csv_file in csv_files:
        with open(csv_file, "r") as f:
            reader = csv.reader(f)
            for row_i, row in enumerate(reader):
                if row_i == 0:  # header
                    assert row == ["token", "rate"]
                elif row_i == 1:
                    token = row[0].upper()
                    rate = float(row[1])
                    rates[token] = rate
                else:
                    raise ValueError("csv should only have two rows")
        print(f"Loaded {csv_file}")

    return rates


@enforce_types
def rateCsvFilenames(csv_dir: str) -> List[str]:
    """Returns a list of exchange rate filenames in this directory"""
    return glob.glob(os.path.join(csv_dir, "rate*.csv"))


@enforce_types
def rateCsvFilename(token_symbol: str, csv_dir: str) -> str:
    """Returns the exchange rate filename for a given token"""
    return os.path.join(csv_dir, f"rate-{token_symbol.upper()}.csv")


# ========================================================================
# rewards csvs


@enforce_types
def saveRewardsperlpCsv(
    rewards: Dict[str, Dict[str, float]], csv_dir: str, token_symbol: str
):
    """
    @description
      Save the rewards dict as a csv,

    @arguments
      rewards -- dict of [chainID][LP_addr] : value (float, *not* base 18)
      ..
    """
    token_symbol = token_symbol.upper()
    csv_file = rewardsperlpCsvFilename(csv_dir, token_symbol)
    assert not os.path.exists(csv_file), f"{csv_file} can't already exist"
    with open(csv_file, "w") as f:
        writer = csv.writer(f)
        writer.writerow(["chainID", "LP_addr", f"{token_symbol}_amt"])
        for chainID, innerdict in rewards.items():
            for LP_addr, value in innerdict.items():
                writer.writerow([chainID, LP_addr, value])
    print(f"Created {csv_file}")


@enforce_types
def saveRewardsinfoCsv(
    rewards: Dict[str, Dict[str, Dict[str, float]]], csv_dir: str, token_symbol: str
):
    """
    @description
      Save the rewards dict as a csv,

    @arguments
      rewards -- dict of [chainID][pool_addr][LP_addr] : value (float, *not* base 18)
      ..
    """
    token_symbol = token_symbol.upper()
    csv_file = rewardsinfoCsvFilename(csv_dir, token_symbol)
    assert not os.path.exists(csv_file), f"{csv_file} can't already exist"
    with open(csv_file, "w") as f:
        writer = csv.writer(f)
        writer.writerow(["chainID", "pool_addr", "LP_addr", "amt", "token"])
        for chainID, innerdict in rewards.items():
            for LP_addr, innerdict2 in innerdict.items():
                for pool_addr, value in innerdict2.items():
                    writer.writerow([chainID, LP_addr, pool_addr, value, token_symbol])
    print(f"Created {csv_file}")


@enforce_types
def loadRewardsCsv(csv_dir: str, token_symbol: str) -> Dict[str, Dict[str, float]]:
    """Loads rewards -- dict of [chainID][LP_addr] : value, from csv"""
    token_symbol = token_symbol.upper()
    csv_file = rewardsperlpCsvFilename(csv_dir, token_symbol)
    rewards: Dict[Any, Dict[str, float]] = {}

    with open(csv_file, "r") as f:
        reader = csv.reader(f)
        for row_i, row in enumerate(reader):
            if row_i == 0:  # header
                assert row == ["chainID", "LP_addr", f"{token_symbol}_amt"]
            else:
                chainID, LP_addr, amt = int(row[0]), row[1], float(row[2])
                if chainID not in rewards:
                    rewards[chainID] = {}
                assert LP_addr not in rewards[chainID], "duplicate found"
                rewards[chainID][LP_addr] = amt
    print(f"Loaded {csv_file}")

    return rewards


@enforce_types
def rewardsperlpCsvFilename(csv_dir: str, token_symbol: str) -> str:
    return os.path.join(csv_dir, f"rewardsperlp-{token_symbol.upper()}.csv")


@enforce_types
def rewardsinfoCsvFilename(csv_dir: str, token_symbol: str) -> str:
    return os.path.join(csv_dir, f"rewardsinfo-{token_symbol.upper()}.csv")


# =======================================================================
# helper funcs


@enforce_types
def _lastInt(s: str) -> int:
    """Return the last integer in the given str"""
    nbr_strs = re.findall("[0-9]+", s)
    return int(nbr_strs[-1])
