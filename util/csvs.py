import csv
from enforce_typing import enforce_types
import glob
import os
from typing import Dict, List

#========================================================================
#stakes csvs

@enforce_types
def saveStakesCsv(stakes:dict, csv_dir:str, network:str):
    """
    @description
      Save the stakes csv for this network

    @arguments
      stakes -- dict of [pool_addr][LP_addr] : stake
      ..
    """
    assert os.path.exists(csv_dir), csv_dir
    csv_file = stakesCsvFilename(csv_dir, network)
    assert not os.path.exists(csv_file), csv_file
    with open(csv_file, "w") as f:
        writer = csv.writer(f)
        writer.writerow(["pool_address", "LP_address", "stake_amount"])
        for pool_addr, d in stakes.items():
            for LP_addr, stake in d.items():
                writer.writerow([pool_addr, LP_addr, stake])
    print(f"Created {csv_file}")

@enforce_types
def loadStakesCsvs(csv_dir:str):
    """
    @description
      Load all stakes csvs, and return result as a single dict

    @return
      stakes -- dict of [pool_addr][LP_addr]:stake, from csvs in dir
    """
    csv_files = stakesCsvFilenames(csv_dir)
    stakes = {}
    for csv_file in csv_files:
        with open(csv_file, "r") as f:
            reader = csv.reader(f)
            for row_i, row in enumerate(reader):
                if row_i == 0: #header
                    continue
                pool_addr, LP_addr, stake = row[0], row[1], float(row[2])
                if pool_addr not in stakes:
                    stakes[pool_addr] = {}
                assert LP_addr not in stakes[pool_addr], "duplicate found"
                stakes[pool_addr][LP_addr] = stake
        print(f"Loaded {csv_file}")

    return stakes

@enforce_types
def stakesCsvFilenames(csv_dir:str) -> List[str]:
    """Returns a list of stakes filenames in this directory"""
    return glob.glob(os.path.join(csv_dir, "stakes*.csv"))

@enforce_types
def stakesCsvFilename(csv_dir:str, network:str) -> str:
    """Returns the stakes filename for a given network"""
    return os.path.join(csv_dir, f"stakes-{network}.csv")

#========================================================================
#pool_vols csvs

@enforce_types
def savePoolVolsCsv(pool_vols:dict, csv_dir:str, network:str):
    """
    @description
      Save the pool_vols csv for this network

    @arguments
      pool_vols -- dict of [pool_addr] : vol
      ..
    """
    assert os.path.exists(csv_dir), csv_dir
    csv_file = poolVolsCsvFilename(csv_dir, network)
    assert not os.path.exists(csv_file), csv_file
    with open(csv_file, "w") as f:
        writer = csv.writer(f)
        writer.writerow(["pool_address", "vol_amount"])
        for pool_addr, vol in pool_vols.items():
            writer.writerow([pool_addr, vol])
    print(f"Created {csv_file}")

@enforce_types
def loadPoolVolsCsvs(csv_dir:str):
    """
    @description
      Load all pool_vols csvs, and return result as a single dict

    @return
      pool_vols -- dict of [pool_addr]:vol, from csvs in dir
    """
    csv_files = poolVolsCsvFilenames(csv_dir)
    pool_vols = {}
    for csv_file in csv_files:
        with open(csv_file, "r") as f:
            reader = csv.reader(f)
            for row_i, row in enumerate(reader):
                if row_i == 0: #header
                    continue
                pool_addr, vol = row[0], float(row[1])
                assert pool_addr not in pool_vols, "duplicate found"
                pool_vols[pool_addr] = vol
        print(f"Loaded {csv_file}")

    return pool_vols

@enforce_types
def poolVolsCsvFilenames(csv_dir:str) -> List[str]:
    """Returns a list of pool_vols filenames in this directory"""
    return glob.glob(os.path.join(csv_dir, "pool_vols*.csv"))

@enforce_types
def poolVolsCsvFilename(csv_dir:str, network) -> str:
    """Returns the pool_vols filename for a given network"""
    return os.path.join(csv_dir, f"pool_vols-{network}.csv")

#========================================================================
#exchange rate csvs

@enforce_types
def saveRateCsv(token_symbol:str, USD_per_token:float, csv_dir:str) -> str:
    """
    @description
      Save a csv file for an exchange rate.

    @arguments
      token_symbol -- str -- e.g. "OCEAN", "H2O"
      USD_per_token -- float -- e.g. 0.86
      csv_dir -- directory holding csvs
    """
    csv_file = rateCsvFilename(token_symbol, csv_dir)
    assert not os.path.exists(csv_file), f"{csv_file} can't already exist"
    with open(csv_file, "w") as f:
        writer = csv.writer(f)
        writer.writerow(["token_symbol", "USD_per_token"])
        writer.writerow([token_symbol, str(USD_per_token)])
    print(f"Created {csv_file}")

@enforce_types
def loadRateCsvs(csv_dir:str):
    """
    @description
      Load all exchange rate csvs, and return result as a single dict

    @return
      rates -- dict of [token_symbol]:USD_per_token, from csvs
    """
    csv_files = rateCsvFilenames(csv_dir)
    rates = {}
    for csv_file in csv_files:
        with open(csv_file, "r") as f:
            reader = csv.reader(f)
            for row_i, row in enumerate(reader):
                if row_i == 0: #header
                    continue
                else: #row_i == 1:
                    symbol, USD_per_token = row[0], float(row[1])
                    rates[token_symbol] = USD_per_token
                    break
        print(f"Loaded {csv_file}")

    return rates
    
@enforce_types
def rateCsvFilenames(csv_dir:str) -> List[str]:
    """Returns a list of exchange rate filenames in this directory"""
    return glob.glob(os.path.join(csv_dir, "rate*.csv"))

@enforce_types
def rateCsvFilename(token_symbol:str, csv_dir:str) -> str:
    """Returns the exchange rate filename for a given token"""
    return os.path.join(csv_dir, f"rate-{token_symbol}.csv")

#========================================================================
#rewards csvs

@enforce_types
def saveRewardsCsv(rewards:Dict[str,float], csv_dir:str):
    """
    @description
      Save the rewards dict as a csv,

    @arguments
      rewards -- dict of [to_addr] : value_float (*not* base 18)
      ..
    """
    csv_file = rewardsCsvFilename(csv_dir)
    assert not os.path.exists(csv_file), f"{csv_file} can't already exist"
    with open(csv_file, "w") as f:
        writer = csv.writer(f)
        writer.writerow(["LP_address", "OCEAN_float"])
        for to_addr, value in rewards.items():
            writer.writerow([to_addr, value])
    print(f"Created {csv_file}")

@enforce_types
def loadRewardsCsv(csv_dir:str) -> Dict[str,float]:
    """Loads rewards -- dict of [LP_addr]:OCEAN_float (not wei), from csv"""
    csv_file = rewardsCsvFilename(csv_dir)
    rewards = {}
    
    with open(csv_file, "r") as f:
        reader = csv.reader(f)
        for row_i, row in enumerate(reader):
            if row_i == 0: #header
                continue
            LP_addr, OCEAN_float = row[0], float(row[1])
            assert LP_addr not in rewards, "duplicate found"
            rewards[LP_addr] = OCEAN_float
    print(f"Loaded {csv_file}")

    return rewards

@enforce_types
def rewardsCsvFilename(csv_dir:str) -> str:
    return os.path.join(csv_dir, "rewards-OCEAN.csv")


