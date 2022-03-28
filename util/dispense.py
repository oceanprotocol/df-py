import csv
import os

from util.constants import BROWNIE_PROJECT

def deployContract():
    """Deploy new claims contract"""
    pass
    # return BROWNIE_PROJECT.ClaimsContract.deploy(
    #     "TST", "Test Token", 18, 1e21, {"from": accounts[0]}
    # )

def dispenseRewards(csv_dir:str):
    """@arguments -- csv_dir -- directory path for csv file"""
    pass

def rewardsPathToFile(path:str) -> str:
    return os.path.join(path, 'rewards.csv')

def rewardsToCsv(rewards:dict, csv_dir:str) -> str:
    """
    @description
      Given rewards dict, store is as csv:

      address  OCEAN_reward  
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
        writer.writerow(["address", "OCEAN_reward"])
        for address, OCEAN_reward in rewards.items():
            writer.writerow([address, OCEAN_reward])
    print(f"Filled rewards file: {csv_file}")

def csvToRewards(dir):
    """
    @description
      Given rewards csv, extract it as dict

    @arguments
      csv_dir -- directory path for csv file

    @return
      rewards -- dict of [LP_addr] : OCEAN_float
    """
    csv_file = rewardsPathToFile(csv_dir)
    rewards = {}
    with open(csv_file, 'r') as f:
        reader = csv.writer(f)
        for row_i, row in enumerate(reader):
            if row_i > 0:
                (address, OCEAN_reward) = row
                rewards[address] = OCEAN_reward
    return rewards

