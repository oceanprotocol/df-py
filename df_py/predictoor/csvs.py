import csv
import os
from typing import Dict, Union

from enforce_typing import enforce_types

from df_py.predictoor.models import Predictoor, PredictoorBase
from df_py.util.csv_helpers import assertIsEthAddr


@enforce_types
def savePredictoorData(
    predictoor_data: Dict[str, Union[PredictoorBase, Predictoor]],
    csv_dir: str,
    chainid: int,
):
    assert os.path.exists(csv_dir), csv_dir
    csv_file = predictoorDataFilename(csv_dir, chainid)
    assert not os.path.exists(csv_file), csv_file

    with open(csv_file, "w") as f:
        writer = csv.writer(f)
        row = ["predictoor_addr", "accuracy", "n_preds", "n_correct_preds"]
        writer.writerow(row)
        for predictoor in predictoor_data.values():
            accuracy = predictoor.accuracy
            predictoor_addr = predictoor.address
            n_preds = predictoor.prediction_count
            n_correct_preds = predictoor.correct_prediction_count
            assertIsEthAddr(predictoor_addr)
            row = [
                predictoor_addr.lower(),
                str(accuracy),
                str(n_preds),
                str(n_correct_preds),
            ]
            writer.writerow(row)
    print(f"Created {csv_file}")


@enforce_types
def loadPredictoorData(csv_dir: str, chainid: int) -> Dict[str, PredictoorBase]:
    csv_file = predictoorDataFilename(csv_dir, chainid)
    predictoor_data = {}
    with open(csv_file, "r") as f:
        reader = csv.reader(f)
        for row_i, row in enumerate(reader):
            if row_i == 0:
                assert row == [
                    "predictoor_addr",
                    "accuracy",
                    "n_preds",
                    "n_correct_preds",
                ]
                continue
            predictoor_addr, accuracy_s, n_preds_s, n_correct_preds_s = row
            predictoor_addr = predictoor_addr.lower()
            accuracy = float(accuracy_s)
            n_preds = int(n_preds_s)
            n_correct_preds = int(n_correct_preds_s)
            assertIsEthAddr(predictoor_addr)

            predictoor = PredictoorBase(
                predictoor_addr, n_preds, n_correct_preds, accuracy
            )

            predictoor_data[predictoor_addr] = predictoor

    print(f"Loaded {csv_file}")
    return predictoor_data


@enforce_types
def predictoorDataFilename(csv_dir, chainid):
    f = f"predictoordata_{chainid}.csv"
    return os.path.join(csv_dir, f)

# ------------------------------- REWARDS -------------------------------


@enforce_types
def savePredictoorRewards(
    predictoor_rewards: Dict[str, float],
    csv_dir: str,
):
    assert os.path.exists(csv_dir), csv_dir
    csv_file = predictoorRewardsFilename(csv_dir)
    assert not os.path.exists(csv_file), csv_file

    with open(csv_file, "w") as f:
        writer = csv.writer(f)
        row = ["predictoor_addr", "reward"]
        writer.writerow(row)
        for predictoor_addr, reward in predictoor_rewards.items():
            assertIsEthAddr(predictoor_addr)
            row = [predictoor_addr.lower(), str(reward)]
            writer.writerow(row)
    print(f"Created {csv_file}")


@enforce_types
def loadPredictoorRewards(csv_dir: str) -> Dict[str, float]:
    csv_file = predictoorRewardsFilename(csv_dir)
    predictoor_rewards = {}
    with open(csv_file, "r") as f:
        reader = csv.reader(f)
        for row_i, row in enumerate(reader):
            if row_i == 0:
                assert row == ["predictoor_addr", "reward"]
                continue
            predictoor_addr, reward_s = row
            predictoor_addr = predictoor_addr.lower()
            reward = float(reward_s)
            assertIsEthAddr(predictoor_addr)

            predictoor_rewards[predictoor_addr] = reward

    print(f"Loaded {csv_file}")
    return predictoor_rewards


@enforce_types
def predictoorRewardsFilename(csv_dir):
    f = f"predictoor_rewards.csv"
    return os.path.join(csv_dir, f)
