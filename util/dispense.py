import csv
import os

from util import oceanutil
from util.constants import BROWNIE_PROJECT as B
from util.base18 import fromBase18, toBase18

def dispenseRewards(csv_dir:str, airdrop_contract_addr:str, from_account):
    """@arguments -- csv_dir -- directory path for csv file"""
    raise NotImplementedError()
    
def rewardsPathToFile(path:str) -> str:
    return os.path.join(path, 'rewards.csv')

def rewardsToCsv(rewards:dict, csv_dir:str) -> str:
    """
    @description
      Given rewards dict, store as csv:

      address  amt_OCEAN
      0x123    123.123
      0x456    456.456
      ..       ..

    @arguments
      rewards -- dict of [LP_addr] : OCEAN_float
      csv_dir -- directory path for csv file
    """
    csv_file = rewardsPathToFile(csv_dir)
    assert not os.path.exists(csv_file), f"{csv_file} can't already exist"
    with open(csv_file, 'w') as f:
        writer = csv.writer(f)
        writer.writerow(["address", "amt_OCEAN"])
        for address, OCEAN_reward in rewards.items():
            writer.writerow([address, OCEAN_reward])
    print(f"Filled rewards file: {csv_file}")

def csvToRewards(csv_dir):
    """
    @description
      Given rewards csv, extract it as dict

    @arguments
      csv_dir -- directory path for csv file

    @return
      rewards -- dict of [address_str] : amt_OCEAN_float
    """
    csv_file = rewardsPathToFile(csv_dir)
    rewards = {}
    with open(csv_file, 'r') as f:
        reader = csv.reader(f)
        for row_i, row in enumerate(reader):
            if row_i > 0:
                address = row[0]
                OCEAN_reward = float(row[1])
                rewards[address] = OCEAN_reward
    return rewards

