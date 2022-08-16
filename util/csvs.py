import csv
import glob
import os
import re
from typing import Any, Dict, List
from enforce_typing import enforce_types

from util import constants, oceanutil


# ========================================================================
# allocation csvs


@enforce_types
def saveAllocationCsv(allocations: dict, csv_dir: str):
    """
    @description
      Save the stakes csv for this chain. This csv is a key input for
      dftool calcrewards, and contains just enough info for it to operate, and no more.

    @arguments
      allocations -- dict of [chain_id][nft_addr][LP_addr] : percent
      csv_dir -- directory that holds csv files
    """
    assert os.path.exists(csv_dir), csv_dir
    csv_file = allocationCsvFilename(csv_dir)
    assert not os.path.exists(csv_file), csv_file
    S = allocations
    with open(csv_file, "w") as f:
        writer = csv.writer(f)
        row = ["chainID", "nft_addr", "LP_addr", "percent"]
        writer.writerow(row)
        for chainID in S.keys():
            for nft_addr in S[chainID].keys():
                assertIsEthAddr(nft_addr)
                for LP_addr, percent in S[chainID][nft_addr].items():
                    assertIsEthAddr(nft_addr)
                    row = [
                        chainID,
                        nft_addr.lower(),
                        LP_addr.lower(),
                        percent,
                    ]
                    writer.writerow(row)
    print(f"Created {csv_file}")


@enforce_types
def loadAllocationCsvs(csv_dir: str):
    """
    @description
      Load all stakes csvs (across all chains); return result as a single dict

    @return
      stakes -- dict of [chainID][basetoken_addr][pool_addr][LP_addr] : stake_amt
    """
    csv_files = stakesCsvFilenames(csv_dir)
    stakes = {}
    for csv_file in csv_files:
        chainID = chainIDforStakeCsv(csv_file)
        stakes[chainID] = loadStakesCsv(csv_dir, chainID)
    return stakes


@enforce_types
def allocationCsvFilenames(csv_dir: str) -> List[str]:
    """Returns a list of allocation filenames in this directory"""
    return glob.glob(os.path.join(csv_dir, "allocation*.csv"))


@enforce_types
def allocationCsvFilename(csv_dir: str) -> str:
    """Returns the allocation filename for a given chainID"""
    return os.path.join(csv_dir, f"allocations.csv")


@enforce_types
def chainIDforStakeCsv(filename) -> int:
    """Returns chainID for a given allocation csv filename"""
    return _lastInt(filename)


# ========================================================================
# poolvols csvs


@enforce_types
def savePoolvolsCsv(poolvols_at_chain: dict, csv_dir: str, chainID: int):
    """
    @description
      Save the poolvols csv for this chain. This csv is a key input for
      dftool calcrewards, and contains just enough info for it to operate, and no more.

    @arguments
      poolvols_at_chain -- dict of [basetoken_addr][pool_addr] : vol_amt
      csv_dir -- directory that holds csv files
      chainID -- which network
    """
    assert os.path.exists(csv_dir), csv_dir
    csv_file = poolvolsCsvFilename(csv_dir, chainID)
    assert not os.path.exists(csv_file), csv_file
    V = poolvols_at_chain
    with open(csv_file, "w") as f:
        writer = csv.writer(f)
        writer.writerow(["chainID", "basetoken_addr", "pool_addr", "vol_amt"])
        for basetoken_addr in V.keys():
            assertIsEthAddr(basetoken_addr)
            for pool_addr, vol in V[basetoken_addr].items():
                assertIsEthAddr(pool_addr)
                row = [chainID, basetoken_addr.lower(), pool_addr.lower(), vol]
                writer.writerow(row)
    print(f"Created {csv_file}")


@enforce_types
def loadPoolvolsCsvs(csv_dir: str):
    """
    @description
      Load all poolvols csvs (across all chains); return result as single dict

    @return
      poolvols -- dict of [chainID][basetoken_addr][pool_addr] : vol_amt
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
      poolvols_at_chain -- dict of [basetoken_addr][pool_addr] : vol_amt
    """
    csv_file = poolvolsCsvFilename(csv_dir, chainID)
    V: Dict[str, Dict[str, float]] = {}  # ie poolvols_at_chain
    with open(csv_file, "r") as f:
        reader = csv.reader(f)
        for row_i, row in enumerate(reader):
            if row_i == 0:  # header
                assert row == ["chainID", "basetoken_addr", "pool_addr", "vol_amt"]
                continue

            chainID2 = int(row[0])
            basetoken_addr = row[1].lower()
            pool_addr = row[2].lower()
            vol_amt = float(row[3])

            assert chainID2 == chainID, "csv had data from different chain"
            assertIsEthAddr(basetoken_addr)
            assertIsEthAddr(pool_addr)

            if basetoken_addr not in V:
                V[basetoken_addr] = {}
            assert pool_addr not in V[basetoken_addr], "duplicate found"
            V[basetoken_addr][pool_addr] = vol_amt
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
# approved csvs


@enforce_types
def saveApprovedCsv(
    approved_token_addrs_at_chain: List[str], csv_dir: str, chainID: int
):
    """
    @description
      Save the approved tokens for this chain

    @arguments
      approved_token_addrs_at_chain --
      csv_dir -- directory that holds csv files
      chainID -- which chain (network)

    @note
      We explicitly do *not* track symbols here, since (C1, addr) is enough, and tracking
      symbols adds complexity and makes things error-prone. Eg. mOCEAN vs OCEAN.
    """
    assert os.path.exists(csv_dir), csv_dir
    csv_file = approvedCsvFilename(csv_dir, chainID)
    assert not os.path.exists(csv_file), csv_file
    with open(csv_file, "w") as f:
        writer = csv.writer(f)
        writer.writerow(["chainID", "token_addr"])
        for token_addr in approved_token_addrs_at_chain:
            assertIsEthAddr(token_addr)
            row = [chainID, token_addr.lower()]
            writer.writerow(row)

    print(f"Created {csv_file}")


@enforce_types
def loadApprovedCsvs(csv_dir: str) -> Dict[int, List[str]]:
    """
    @description
      Load all approved tokens across all chains

    @return
      approved_token_addrs -- dict of [chainID] : list_of_addr
    """
    csv_files = approvedCsvFilenames(csv_dir)
    approved_token_addrs: dict = {}
    for csv_file in csv_files:
        chainID = chainIDforApprovedCsv(csv_file)
        approved_token_addrs[chainID] = loadApprovedCsv(csv_dir, chainID)

    return approved_token_addrs


@enforce_types
def loadApprovedCsv(csv_dir: str, chainID: int) -> List[str]:
    """
    @description
      Load approved tokens for this chainID

    @return
      approved_token_addrs_at_chain --
    """
    csv_file = approvedCsvFilename(csv_dir, chainID)
    approved_token_addrs_at_chain: List[str] = []
    with open(csv_file, "r") as f:
        reader = csv.reader(f)
        for row_i, row in enumerate(reader):
            if row_i == 0:  # header
                assert row == ["chainID", "token_addr"]
                continue

            chainID2 = int(row[0])
            token_addr = row[1].lower()

            assert chainID2 == chainID, "csv had data from different chain"
            assertIsEthAddr(token_addr)

            approved_token_addrs_at_chain.append(token_addr)

    print(f"Loaded {csv_file}")
    return approved_token_addrs_at_chain


@enforce_types
def approvedCsvFilenames(csv_dir: str) -> List[str]:
    """Returns a list of approved filenames in this directory"""
    return glob.glob(os.path.join(csv_dir, "approved*.csv"))


@enforce_types
def approvedCsvFilename(csv_dir: str, chainID: int) -> str:
    """Returns the approved filename for a given chainID"""
    return os.path.join(csv_dir, f"approved-{chainID}.csv")


@enforce_types
def chainIDforApprovedCsv(filename) -> int:
    """Returns chainID for a given approved csv filename"""
    return _lastInt(filename)


# ========================================================================
# symbols csvs


@enforce_types
def saveSymbolsCsv(symbols_at_chain: Dict[str, str], csv_dir: str, chainID: int):
    """
    @description
      Save the symbols tokens for this chain

    @arguments
      symbols_at_chain -- dict of [basetoken_addr] : basetoken_symbol
      csv_dir -- directory that holds csv files
      chainID -- which chain (network)
    """
    assert os.path.exists(csv_dir), csv_dir
    csv_file = symbolsCsvFilename(csv_dir, chainID)
    assert not os.path.exists(csv_file), csv_file
    with open(csv_file, "w") as f:
        writer = csv.writer(f)
        writer.writerow(["chainID", "token_addr", "token_symbol"])
        for token_addr, token_symbol in symbols_at_chain.items():
            assertIsEthAddr(token_addr)
            row = [
                chainID,
                token_addr.lower(),
                token_symbol.upper(),
            ]
            writer.writerow(row)

    print(f"Created {csv_file}")


@enforce_types
def loadSymbolsCsvs(csv_dir: str) -> Dict[int, Dict[str, str]]:
    """
    @description
      Load all symbols tokens across all chains

    @return
      symbols -- dict of [chainID][basetoken_addr] : basetoken_symbol
    """
    csv_files = symbolsCsvFilenames(csv_dir)
    symbols: dict = {}
    for csv_file in csv_files:
        chainID = chainIDforSymbolsCsv(csv_file)
        symbols[chainID] = loadSymbolsCsv(csv_dir, chainID)

    return symbols


@enforce_types
def loadSymbolsCsv(csv_dir: str, chainID: int) -> Dict[str, str]:
    """
    @description
      Load symbols for this chainID

    @return
      symbols_at_chain -- dict of [basetoken_addr] : basetoken_symbol
    """
    csv_file = symbolsCsvFilename(csv_dir, chainID)
    symbols_at_chain: dict = {}
    with open(csv_file, "r") as f:
        reader = csv.reader(f)
        for row_i, row in enumerate(reader):
            if row_i == 0:  # header
                assert row == ["chainID", "token_addr", "token_symbol"]
                continue

            chainID2 = int(row[0])
            token_addr = row[1].lower()
            token_symbol = row[2].upper()

            assert chainID2 == chainID, "csv had data from different chain"
            assertIsEthAddr(token_addr)

            symbols_at_chain[token_addr] = token_symbol

    print(f"Loaded {csv_file}")
    return symbols_at_chain


@enforce_types
def symbolsCsvFilenames(csv_dir: str) -> List[str]:
    """Returns a list of symbols filenames in this directory"""
    return glob.glob(os.path.join(csv_dir, "symbols*.csv"))


@enforce_types
def symbolsCsvFilename(csv_dir: str, chainID: int) -> str:
    """Returns the symbols filename for a given chainID"""
    return os.path.join(csv_dir, f"symbols-{chainID}.csv")


@enforce_types
def chainIDforSymbolsCsv(filename) -> int:
    """Returns chainID for a given symbols csv filename"""
    return _lastInt(filename)


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
        writer.writerow(["token_symbol", "rate"])
        writer.writerow([token_symbol, str(rate)])
    print(f"Created {csv_file}")


@enforce_types
def loadRateCsvs(csv_dir: str) -> Dict[str, float]:
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
                    assert row == ["token_symbol", "rate"]
                elif row_i == 1:
                    token_symbol = row[0].upper()
                    rate = float(row[1])
                    rates[token_symbol] = rate
                else:
                    raise ValueError("csv should only have two rows")
        print(f"Loaded {csv_file}")

    # have rates for non-standard token names like MOCEAN
    if "OCEAN" in rates:
        rates["MOCEAN"] = rates["OCEAN"]

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
# rewardsperlp csvs


@enforce_types
def saveRewardsperlpCsv(
    rewards: Dict[str, Dict[str, float]], csv_dir: str, token_symbol: str
):
    """
    @description
      Save the rewards dict as a "rewardsperlp" csv. This csv is the key input for
      dftool dispense, and contains just enough info for it to operate, and no more.

    @arguments
      rewards -- dict of [chainID][LP_addr] : value (float, *not* integers / wei)
      ..
    """
    token_symbol = token_symbol.upper()
    csv_file = rewardsperlpCsvFilename(csv_dir, token_symbol)
    assert not os.path.exists(csv_file), f"{csv_file} can't already exist"
    with open(csv_file, "w") as f:
        writer = csv.writer(f)

        header = ["chainID", "LP_addr", f"{token_symbol}_amt"]
        writer.writerow(header)

        for chainID, innerdict in rewards.items():
            for LP_addr, value in innerdict.items():
                assertIsEthAddr(LP_addr)
                row = [chainID, LP_addr.lower(), value]
                writer.writerow(row)
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
                chainID = int(row[0])
                LP_addr = row[1].lower()
                amt = float(row[2])

                assertIsEthAddr(LP_addr)
                if chainID not in rewards:
                    rewards[chainID] = {}
                assert LP_addr not in rewards[chainID], "duplicate found"

                rewards[chainID][LP_addr] = amt

    print(f"Loaded {csv_file}")

    return rewards


@enforce_types
def rewardsperlpCsvFilename(csv_dir: str, token_symbol: str) -> str:
    return os.path.join(csv_dir, f"rewardsperlp-{token_symbol.upper()}.csv")


# ========================================================================
# rewardsinfo csvs


@enforce_types
def saveRewardsinfoCsv(
    rewards: Dict[str, Dict[str, Dict[str, float]]], csv_dir: str, token_symbol: str
):
    """
    @description
      Save the rewards dict as a "rewardsinfo" csv. This csv is for the DF webapp,
      so it can have lots of columns, whatever's interesting for the user.

    @arguments
      rewards -- dict of [chainID][pool_addr][LP_addr] : value (float, *not* base 18)
      ..
    """
    token_symbol = token_symbol.upper()
    csv_file = rewardsinfoCsvFilename(csv_dir, token_symbol)
    assert not os.path.exists(csv_file), f"{csv_file} can't already exist"
    with open(csv_file, "w") as f:
        writer = csv.writer(f)

        header = ["chainID", "pool_addr", "LP_addr", "amt", "token"]
        writer.writerow(header)

        for chainID, innerdict in rewards.items():
            for LP_addr, innerdict2 in innerdict.items():
                assertIsEthAddr(LP_addr)
                for pool_addr, value in innerdict2.items():
                    assertIsEthAddr(pool_addr)
                    row = [
                        chainID,
                        LP_addr.lower(),
                        pool_addr.lower(),
                        value,
                        token_symbol,
                    ]
                    writer.writerow(row)
    print(f"Created {csv_file}")


@enforce_types
def rewardsinfoCsvFilename(csv_dir: str, token_symbol: str) -> str:
    return os.path.join(csv_dir, f"rewardsinfo-{token_symbol.upper()}.csv")


# =======================================================================
# helper funcs


@enforce_types
def assertIsEthAddr(s: str):
    # just a basic check
    assert s[:2] == "0x", s


@enforce_types
def _lastInt(s: str) -> int:
    """Return the last integer in the given str"""
    nbr_strs = re.findall("[0-9]+", s)
    return int(nbr_strs[-1])
