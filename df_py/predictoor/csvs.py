import csv
import os
import random
from typing import Dict

from enforce_typing import enforce_types

from df_py.predictoor.models import Predictoor, Prediction, PredictContract
from df_py.util.csv_helpers import assert_is_eth_addr


# ------------------------------- PREDICTOOR DATA -------------------------------
def sample_predictoor_data_csv(num_rows=50000):
    def random_predictor_address():
        return f"0x{random.randint(1, 16):x}"

    def random_slot():
        return random.randint(1, 50)

    def random_payout():
        return random.choice([0.0, 1.0])

    def random_contract_address():
        return f"0xContract{random.randint(1, 3)}"

    result = "predictoor_addr,slot,payout,contract_addr\n"

    for _ in range(num_rows):
        predictor_address = random_predictor_address()
        slot = random_slot()
        payout = random_payout()
        contract_address = random_contract_address()
        result += f"{predictor_address},{slot},{payout},{contract_address}\n"

    return result


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
            assert_is_eth_addr(predictoor.address)
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
def sample_predictoor_summary_csv():
    return """predictoor_addr,contract_addr,prediction_count,correct_prediction_count,accuracy
0x0000000000000000000000000000000000000000,0xContract1,14360,10123,0.70494428969
0x1000000000000000000000000000000000000000,0xContract2,24210,12523,0.51726559273
0x2000000000000000000000000000000000000000,0xContract1,36233,23351,0.64446775039
0x3000000000000000000000000000000000000000,0xContract2,41640,35251,0.84656580211
0x4000000000000000000000000000000000000000,0xContract3,54320,44246,0.81454344624"""


@enforce_types
def save_predictoor_summary_csv(predictoor_data: Dict[str, Predictoor], csv_dir: str):
    """
    Save summaries of each Predictoor's predictions to a CSV file.

    @param predictoor_data: A dictionary containing Predictoor objects.
    @param csv_dir: The directory where the CSV file will be saved.
    """

    csv_file = predictoor_summary_csv_filename(csv_dir)

    fieldnames = [
        "predictoor_addr",
        "contract_addr",
        "prediction_count",
        "correct_prediction_count",
        "accuracy",
    ]

    with open(csv_file, "w", newline="") as csvfile:
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
        writer.writeheader()

        # Writing data rows
        for predictoor_addr, predictoor in predictoor_data.items():
            prediction_summaries = predictoor.prediction_summaries
            for contract_addr, summary in prediction_summaries.items():
                writer.writerow(
                    {
                        "predictoor_addr": predictoor_addr,
                        "contract_addr": contract_addr,
                        "prediction_count": summary.prediction_count,
                        "correct_prediction_count": summary.correct_prediction_count,
                        "accuracy": summary.accuracy,
                    }
                )


@enforce_types
def predictoor_summary_csv_filename(csv_dir):
    f = "predictoor_summary.csv"
    return os.path.join(csv_dir, f)


# ------------------------------- REWARDS -------------------------------
def sample_predictoor_rewards_csv():
    return """predictoor_addr,contract_addr,OCEAN_amt
0x0000000000000000000000000000000000000000,0xContract1,10.0
0x1000000000000000000000000000000000000000,0xContract2,20.0
0x2000000000000000000000000000000000000000,0xContract1,30.0
0x3000000000000000000000000000000000000000,0xContract2,40.0
0x4000000000000000000000000000000000000000,0xContract3,50.0"""


@enforce_types
def save_predictoor_rewards_csv(
    predictoor_rewards: Dict[str, Dict[str, float]], csv_dir: str
):
    assert os.path.exists(csv_dir), csv_dir
    csv_file = predictoor_rewards_csv_filename(csv_dir)
    assert not os.path.exists(csv_file), csv_file

    with open(csv_file, "w") as f:
        writer = csv.writer(f)
        row = ["predictoor_addr", "contract_addr", "OCEAN_amt"]
        writer.writerow(row)

        for predictoor_addr, contracts in predictoor_rewards.items():
            assert_is_eth_addr(predictoor_addr)
            for contract_addr, reward in contracts.items():
                row = [predictoor_addr.lower(), contract_addr.lower(), str(reward)]
                writer.writerow(row)

    print(f"Created {csv_file}")


@enforce_types
def load_predictoor_rewards_csv(csv_dir: str) -> Dict[str, Dict[str, float]]:
    csv_file = predictoor_rewards_csv_filename(csv_dir)
    predictoor_rewards: Dict[str, Dict[str, float]] = {}

    with open(csv_file, "r") as f:
        reader = csv.reader(f)

        for row_i, row in enumerate(reader):
            if row_i == 0:
                assert row == ["predictoor_addr", "contract_addr", "OCEAN_amt"]
                continue
            predictoor_addr, contract_addr, reward_s = row
            predictoor_addr = predictoor_addr.lower()
            contract_addr = contract_addr.lower()
            reward = float(reward_s)
            assert_is_eth_addr(predictoor_addr)
            assert_is_eth_addr(contract_addr)

            if not predictoor_addr in predictoor_rewards:
                predictoor_rewards[predictoor_addr] = {}
            predictoor_rewards[predictoor_addr][contract_addr] = reward

    print(f"Loaded {csv_file}")
    return predictoor_rewards


@enforce_types
def predictoor_rewards_csv_filename(csv_dir):
    f = "predictoor_rewards.csv"
    return os.path.join(csv_dir, f)


# --------------------------- PREDICTOOR CONTRACTS ---------------------------


def sample_predictoor_contracts_csv():
    return """chainid,address,name,symbol,blocks_per_epoch,blocks_per_subscription
1,0xContract1,Contract1,CTR1,100,10
1,0xContract2,Contract2,CTR2,200,20
1,0xContract3,Contract3,CTR3,300,30"""


def save_predictoor_contracts_csv(
    predictoor_contracts: Dict[str, PredictContract], csv_dir: str
):
    assert os.path.exists(csv_dir), csv_dir
    csv_file = os.path.join(csv_dir, "predictoor_contracts.csv")
    assert not os.path.exists(csv_file), csv_file

    fieldnames = [
        "chainid",
        "address",
        "name",
        "symbol",
        "blocks_per_epoch",
        "blocks_per_subscription",
    ]

    with open(csv_file, "w") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for contract in predictoor_contracts.values():
            writer.writerow(contract.to_dict())
    print(f"Created {csv_file}")


def load_predictoor_contracts_csv(csv_dir: str) -> Dict[str, PredictContract]:
    csv_file = os.path.join(csv_dir, "predictoor_contracts.csv")
    contracts: Dict[str, PredictContract] = {}

    with open(csv_file, "r") as f:
        reader = csv.DictReader(f)
        for row in reader:
            contract = PredictContract.from_dict(row)
            contracts[contract.address] = contract

    print(f"Loaded {csv_file}")
    return contracts


def predictoor_contracts_csv_filename(csv_dir):
    f = "predictoor_contracts.csv"
    return os.path.join(csv_dir, f)
