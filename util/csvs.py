import csv
import glob
import os
import re
from typing import Any, Dict, List, Tuple
from enforce_typing import enforce_types

from util.query import DataNFT


# ========================================================================
# allocation csvs


@enforce_types
def saveAllocationCsv(allocs: dict, csv_dir: str, sampled=True):
    """
    @description
      Save the allocations csv for this chain.

    @arguments
      allocs -- dict of [chain_id][nft_addr][LP_addr] : percent_float
      csv_dir -- directory that holds csv files
    """
    assert os.path.exists(csv_dir), csv_dir
    csv_file = allocationCsvFilename(csv_dir, sampled)
    assert not os.path.exists(csv_file), csv_file
    S = allocs
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
def loadAllocationCsvs(csv_dir: str) -> Dict[int, Dict[str, Dict[str, float]]]:
    """
    @description
      Load allocation csv; return result as a single dict

    @return
      allocs -- dict of [chainID][basetoken_addr][nft_addr][LP_addr] : perc_flt
    """
    csv_file = allocationCsvFilename(csv_dir)
    allocs: Dict[int, Dict[str, Dict[str, float]]] = {}
    with open(csv_file, "r") as f:
        reader = csv.reader(f)
        for row_i, row in enumerate(reader):
            if row_i == 0:
                assert row == ["chainID", "nft_addr", "LP_addr", "percent"]
                continue
            _chainID, nft_addr, LP_addr, _percent = row

            chainID = int(_chainID)
            nft_addr = nft_addr.lower()
            LP_addr = LP_addr.lower()
            percent = float(_percent)

            assertIsEthAddr(nft_addr)
            assertIsEthAddr(LP_addr)

            if chainID not in allocs:
                allocs[chainID] = {}

            if nft_addr not in allocs[chainID]:
                allocs[chainID][nft_addr] = {}

            allocs[chainID][nft_addr][LP_addr] = percent
    print(f"Loaded {csv_file}")

    return allocs


@enforce_types
def allocationCsvFilename(csv_dir: str, sampled=True) -> str:
    """Returns the allocations filename"""
    f = "allocations.csv"
    if not sampled:
        f = "allocations_realtime.csv"
    return os.path.join(csv_dir, f)


# ========================================================================
# vebals csvs
def saveVebalsCsv(
    vebals: dict, locked_amt: dict, unlock_time: dict, csv_dir: str, sampled=True
):
    """
    @description
      Save the stakes csv for this chain. This csv is a key input for
      dftool calcrewards, and contains just enough info for it to operate, and no more.

    @arguments
      vebals -- dict of [LP_addr] : balance
      locked_amt -- dict of [LP_addr] : locked_amt
      unlock_time -- dict of [LP_addr] : unlock_time
      csv_dir -- directory that holds csv files
    """
    assert os.path.exists(csv_dir), csv_dir
    csv_file = vebalsCsvFilename(csv_dir, sampled)
    assert not os.path.exists(csv_file), csv_file
    with open(csv_file, "w") as f:
        writer = csv.writer(f)
        row = ["LP_addr", "balance", "locked_amt", "unlock_time"]
        writer.writerow(row)
        for LP_addr in vebals.keys():
            assertIsEthAddr(LP_addr)
            row = [
                LP_addr.lower(),
                vebals[LP_addr],
                locked_amt[LP_addr],
                unlock_time[LP_addr],
            ]
            writer.writerow(row)

    print(f"Created {csv_file}")


def loadVebalsCsv(
    csv_dir: str,
) -> Tuple[Dict[str, float], Dict[str, float], Dict[str, int]]:
    """
    @description
      Load veOCEAN balances csv; return result as a single dict

    @return
      vebals -- dict of [LP_addr] : balance
    """
    csv_file = vebalsCsvFilename(csv_dir)
    vebals: Dict[str, float] = {}
    locked_amts: Dict[str, float] = {}
    unlock_times: Dict[str, int] = {}
    with open(csv_file, "r") as f:
        reader = csv.reader(f)
        for row_i, row in enumerate(reader):
            if row_i == 0:
                assert row == ["LP_addr", "balance", "locked_amt", "unlock_time"]
                continue
            LP_addr, _balance, _locked_amt, _unlock_time = row

            LP_addr = LP_addr.lower()
            balance = float(_balance)
            locked_amt = float(_locked_amt)
            unlock_time = int(_unlock_time)

            assertIsEthAddr(LP_addr)

            vebals[LP_addr] = balance
            locked_amts[LP_addr] = locked_amt
            unlock_times[LP_addr] = unlock_time

    print(f"Loaded {csv_file}")
    return vebals, locked_amts, unlock_times


@enforce_types
def vebalsCsvFilename(csv_dir: str, sampled=True) -> str:
    """Returns the vebals filename"""
    f = "vebals.csv"
    if not sampled:
        f = "vebals_realtime.csv"
    return os.path.join(csv_dir, f)


# ========================================================================
# nftinfo csv


@enforce_types
def saveNftinfoCsv(nftinfo: List[DataNFT], csv_dir: str, chainID: int):
    """
    @description
      Save the nftinfo for this chain. This csv is required for df-sql.

    @arguments
        nftinfo -- list of DataNFT
        csv_dir -- directory that holds csv files
        chainID -- chainID
    """

    assert os.path.exists(csv_dir), csv_dir
    csv_file = nftinfoCsvFilename(csv_dir, chainID)
    assert not os.path.exists(csv_file), csv_file

    with open(csv_file, "w") as f:
        writer = csv.writer(f)
        row = ["chainID", "nft_addr", "did", "symbol", "name", "is_purgatory"]
        writer.writerow(row)

        for nft in nftinfo:
            isinpurg = "0"
            if nft.is_purgatory:
                isinpurg = "1"
            row = [
                str(chainID),
                nft.nft_addr.lower(),
                nft.did,
                nft.symbol,
                nft.name.replace(",", "%@#"),
                isinpurg,
            ]
            writer.writerow(row)


@enforce_types
def nftinfoCsvFilename(csv_dir: str, chainID: int) -> str:
    """Returns the nftinfo filename"""
    return os.path.join(csv_dir, f"nftinfo_{chainID}.csv")


# ========================================================================
# nftvols csvs


@enforce_types
def saveNftvolsCsv(nftvols_at_chain: dict, csv_dir: str, chainID: int):
    """
    @description
      Save the nftvols csv for this chain. This csv is a key input for
      dftool calcrewards, and contains just enough info for it to operate, and no more.

    @arguments
      nftvols_at_chain -- dict of [basetoken_addr][nft_addr] : vol_amt
      csv_dir -- directory that holds csv files
      chainID -- which network
    """
    assert os.path.exists(csv_dir), csv_dir
    csv_file = nftvolsCsvFilename(csv_dir, chainID)
    assert not os.path.exists(csv_file), csv_file
    nftvols = nftvols_at_chain
    with open(csv_file, "w") as f:
        writer = csv.writer(f)
        writer.writerow(["chainID", "basetoken_addr", "nft_addr", "vol_amt"])
        for basetoken_addr in nftvols.keys():
            assertIsEthAddr(basetoken_addr)
            for nft_addr, vol in nftvols[basetoken_addr].items():
                assertIsEthAddr(nft_addr)
                row = [chainID, basetoken_addr.lower(), nft_addr.lower(), vol]
                writer.writerow(row)
    print(f"Created {csv_file}")


@enforce_types
def loadNftvolsCsvs(csv_dir: str):
    """
    @description
      Load all nftvols csvs (across all chains); return result as single dict

    @return
      nftvols -- dict of [chainID][basetoken_addr][nft_addr] : vol_amt
    """
    csv_files = nftvolsCsvFilenames(csv_dir)
    nftvols = {}
    for csv_file in csv_files:
        chainID = chainIDforNftvolsCsv(csv_file)
        nftvols[chainID] = loadNftvolsCsv(csv_dir, chainID)
    return nftvols


@enforce_types
def loadNftvolsCsv(csv_dir: str, chainID: int):
    """
    @description
      Load nftvols for this chainID

    @return
      nftvols_at_chain -- dict of [basetoken_addr][nft_addr] : vol_amt
    """
    csv_file = nftvolsCsvFilename(csv_dir, chainID)
    nftvols: Dict[str, Dict[str, float]] = {}  # ie nftvols_at_chain
    with open(csv_file, "r") as f:
        reader = csv.reader(f)
        for row_i, row in enumerate(reader):
            if row_i == 0:  # header
                assert row == ["chainID", "basetoken_addr", "nft_addr", "vol_amt"]
                continue

            chainID2 = int(row[0])
            basetoken_addr = row[1].lower()
            nft_addr = row[2].lower()
            vol_amt = float(row[3])

            assert chainID2 == chainID, "csv had data from different chain"
            assertIsEthAddr(basetoken_addr)
            assertIsEthAddr(nft_addr)

            if basetoken_addr not in nftvols:
                nftvols[basetoken_addr] = {}
            assert nft_addr not in nftvols[basetoken_addr], "duplicate found"
            nftvols[basetoken_addr][nft_addr] = vol_amt
    print(f"Loaded {csv_file}")

    return nftvols


@enforce_types
def nftvolsCsvFilenames(csv_dir: str) -> List[str]:
    """Returns a list of nftvols filenames in this directory"""
    return glob.glob(os.path.join(csv_dir, "nftvols*.csv"))


@enforce_types
def nftvolsCsvFilename(csv_dir: str, chainID: int) -> str:
    """Returns the nftvols filename for a given chainID"""
    return os.path.join(csv_dir, f"nftvols-{chainID}.csv")


@enforce_types
def chainIDforNftvolsCsv(filename) -> int:
    """Returns chainID for a given nftvols csv filename"""
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
      rewards -- dict of [chainID][nft_addr][LP_addr] : value (float, *not* base 18)
      ..
    """
    token_symbol = token_symbol.upper()
    csv_file = rewardsinfoCsvFilename(csv_dir, token_symbol)
    assert not os.path.exists(csv_file), f"{csv_file} can't already exist"
    with open(csv_file, "w") as f:
        writer = csv.writer(f)

        header = ["chainID", "nft_addr", "LP_addr", "amt", "token"]
        writer.writerow(header)

        for chainID, innerdict in rewards.items():
            for LP_addr, innerdict2 in innerdict.items():
                assertIsEthAddr(LP_addr)
                for nft_addr, value in innerdict2.items():
                    assertIsEthAddr(nft_addr)
                    row = [
                        chainID,
                        LP_addr.lower(),
                        nft_addr.lower(),
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
