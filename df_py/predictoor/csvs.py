import csv
import os
from typing import Dict, Union

from enforce_typing import enforce_types

from df_py.predictoor.models import Predictoor, Prediction
from df_py.util.csv_helpers import assert_is_eth_addr


# ------------------------------- PREDICTOOR DATA -------------------------------
@enforce_types
def save_predictoor_data_csv(
    predictoor_data: Dict[str, Predictoor],
    csv_dir: str,
):
    assert os.path.exists(csv_dir), csv_dir
    csv_file = predictoor_data_csv_filename(csv_dir)
    assert not os.path.exists(csv_file), csv_file

    fieldnames = ['address', 'slot', 'payout', 'contract_addr']
    with open(csv_file, mode='w', newline='') as file:
        writer = csv.DictWriter(file, fieldnames=fieldnames)
        writer.writeheader()
        for predictoor in predictoor_data:
            address = predictoor.address
            for prediction in predictoor._predictions:
                writer.writerow({
                    'address': address,
                    'slot': prediction.slot,
                    'payout': prediction.payout,
                    'contract_addr': prediction.contract_addr
                })

    print(f"Created {csv_file}")



@enforce_types
def load_predictoor_data_csv(csv_dir: str) -> Dict[str, Predictoor]:
    csv_file = predictoor_data_csv_filename(csv_dir)
    
    predictoors = {}
    with open(csv_dir, mode='r') as file:
        csv_reader = csv.DictReader(file)
        for row in csv_reader:
            address = row['address']
            slot = int(row['slot'])
            payout = float(row['payout'])
            contract_addr = row['contract_addr']
            prediction = Prediction(slot, payout, contract_addr)

            if address not in predictoors:
                predictoors[address] = Predictoor(address)
                
            predictoors[address].add_prediction(prediction)
                
    print(f"Loaded {csv_file}")
    return predictoors


@enforce_types
def predictoor_data_csv_filename(csv_dir):
    f = "predictoor_data.csv"
    return os.path.join(csv_dir, f)


# ------------------------------- REWARDS -------------------------------


@enforce_types
def save_predictoor_rewards_csv(predictoor_rewards: Dict[str, float], csv_dir: str):
    assert os.path.exists(csv_dir), csv_dir
    csv_file = predictoor_rewards_csv_filename(csv_dir)
    assert not os.path.exists(csv_file), csv_file

    with open(csv_file, "w") as f:
        writer = csv.writer(f)
        row = ["predictoor_addr", "OCEAN_amt"]
        writer.writerow(row)

        for predictoor_addr, reward in predictoor_rewards.items():
            assert_is_eth_addr(predictoor_addr)
            row = [predictoor_addr.lower(), str(reward)]
            writer.writerow(row)

    print(f"Created {csv_file}")


@enforce_types
def load_predictoor_rewards_csv(csv_dir: str) -> Dict[str, float]:
    csv_file = predictoor_rewards_csv_filename(csv_dir)
    predictoor_rewards = {}

    with open(csv_file, "r") as f:
        reader = csv.reader(f)

        for row_i, row in enumerate(reader):
            if row_i == 0:
                assert row == ["predictoor_addr", "OCEAN_amt"]
                continue
            predictoor_addr, reward_s = row
            predictoor_addr = predictoor_addr.lower()
            reward = float(reward_s)
            assert_is_eth_addr(predictoor_addr)

            predictoor_rewards[predictoor_addr] = reward

    print(f"Loaded {csv_file}")
    return predictoor_rewards


@enforce_types
def predictoor_rewards_csv_filename(csv_dir):
    f = "predictoor_rewards.csv"
    return os.path.join(csv_dir, f)
