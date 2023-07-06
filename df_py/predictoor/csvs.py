import csv
import os
from typing import Dict

from enforce_typing import enforce_types

from df_py.predictoor.models import Predictoor, Prediction
from df_py.util.csv_helpers import assert_is_eth_addr


# ------------------------------- PREDICTOOR DATA -------------------------------
@enforce_types
def sample_predictoor_data_csv():
    return """predictoor_addr,slot,payout,contract_addr
0x1,2,1.0,0xContract1,
0x2,5,1.0,0xContract2,
0x3,8,0.0,0xContract1,
0x1,4,0.0,0xContract2,
0x1,34,1.0,0xContract1,
0x2,23,0.0,0xContract2,
0x2,11,1.0,0xContract2,
0x1,19,0.0,0xContract3,
0x3,6,0.0,0xContract1"""

@enforce_types
def save_predictoor_data_csv(
    predictoor_data: Dict[str, Predictoor],
    csv_dir: str,
):
    assert os.path.exists(csv_dir), csv_dir
    csv_file = predictoor_data_csv_filename(csv_dir)
    assert not os.path.exists(csv_file), csv_file

    fieldnames = ["predictoor_addr", "slot", "payout", "contract_addr"]
    with open(csv_file, mode="w", newline="") as file:
        writer = csv.DictWriter(file, fieldnames=fieldnames)
        writer.writeheader()
        for predictoor in predictoor_data.values():
            for prediction in predictoor._predictions:
                writer.writerow(
                    {
                        "predictoor_addr": predictoor.address,
                        "contract_addr": prediction.contract_addr,
                        "slot": prediction.slot,
                        "payout": prediction.payout,
                    }
                )

    print(f"Created {csv_file}")


@enforce_types
def load_predictoor_data_csv(csv_dir: str) -> Dict[str, Predictoor]:
    csv_file = predictoor_data_csv_filename(csv_dir)

    predictoors = {}
    with open(csv_file, mode="r") as file:
        csv_reader = csv.DictReader(file)
        for row in csv_reader:
            address = row["predictoor_addr"]
            contract_addr = row["contract_addr"]
            slot = int(row["slot"])
            payout = float(row["payout"])
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

# ------------------------------- PREDICTOOR SUMMARY -------------------------------

@enforce_types
def save_predictoor_summary_csv(predictoor_data: Dict[str, Predictoor], csv_dir: str):
    """
    Save summaries of each Predictoor's predictions to a CSV file.

    @param predictoor_data: A dictionary containing Predictoor objects.
    @param csv_dir: The directory where the CSV file will be saved.
    """

    csv_file = predictoor_summary_csv_filename(csv_dir)
    
    fieldnames = ['predictoor_addr', 'contract_addr', 'prediction_count', 'correct_prediction_count', 'accuracy']

    with open(csv_file, 'w', newline='') as csvfile:
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
        writer.writeheader()

        # Writing data rows
        for predictoor_addr, predictoor in predictoor_data.items():
            prediction_summaries = predictoor.prediction_summaries
            for contract_addr, summary in prediction_summaries.items():
                writer.writerow({
                    'predictoor_addr': predictoor_addr,
                    'contract_addr': contract_addr,
                    'prediction_count': summary.prediction_count,
                    'correct_prediction_count': summary.correct_prediction_count,
                    'accuracy': summary.accuracy
                })
                

@enforce_types
def predictoor_summary_csv_filename(csv_dir):
    f = "predictoor_summary.csv"
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
