from enforce_typing import enforce_types

from df_py.predictoor import csvs
from df_py.predictoor.models import Prediction, Predictoor


@enforce_types
def test_predictoordata(tmp_path):
    target_csv = """predictoor_addr,accuracy,n_preds,n_correct_preds
0x0000000000000000000000000000000000000000,0.4,5,2
0x1000000000000000000000000000000000000000,0.4,5,2
0x2000000000000000000000000000000000000000,0.4,5,2
0x3000000000000000000000000000000000000000,0.4,5,2
0x4000000000000000000000000000000000000000,0.4,5,2
0x5000000000000000000000000000000000000000,0.4,5,2
0x6000000000000000000000000000000000000000,0.4,5,2
0x7000000000000000000000000000000000000000,0.4,5,2
0x8000000000000000000000000000000000000000,0.4,5,2
0x9000000000000000000000000000000000000000,0.4,5,2"""

    predictoors = {}
    for i in range(10):
        p = Predictoor(f"0x{i}000000000000000000000000000000000000000")
        for j in range(5):
            p.add_prediction(
                Prediction(i, j % 2 * 1.0, "0x0000000000000000000000000000000000000000")
            )
        predictoors[p.address] = p

    csv_dir = str(tmp_path)
    csvs.savePredictoorData(predictoors, csv_dir, 1)

    with open(csvs.predictoorDataFilename(csv_dir, 1), "r") as loaded_data:
        data = loaded_data.read().strip()
        assert data == target_csv

    loaded_predictoors = csvs.loadPredictoorData(csv_dir, 1)
    assert len(loaded_predictoors) == len(predictoors)

    for addr, original_predictoor in predictoors.items():
        loaded_predictoor = loaded_predictoors[addr]
        assert loaded_predictoor.accuracy == original_predictoor.accuracy
        assert (
            loaded_predictoor.prediction_count == original_predictoor.prediction_count
        )
        assert (
            loaded_predictoor.correct_prediction_count
            == original_predictoor.correct_prediction_count
        )

@enforce_types
def test_loadAllPredictoorData(tmp_path):
    # create multiple CSVs for each chain_id
    csv_dir = str(tmp_path)
    chain_ids = [1, 2, 3]
    predictoor_data = {}
    for chainid in chain_ids:
        predictoors = {}
        for i in range(5):  # 5 predictoors per chain
            p = Predictoor(f"0x{i}00000000000000000000000000000000000000{chainid}")
            for j in range(5):
                p.add_prediction(
                    Prediction(i, j % 2 * 1.0, "0x0000000000000000000000000000000000000000")
                )
            predictoors[p.address] = p

        csvs.savePredictoorData(predictoors, csv_dir, chainid)

        predictoor_data.update(predictoors)

    loaded_predictoors = csvs.loadAllPredictoorData(csv_dir)

    # loaded data should be equal to the originally created data
    assert len(loaded_predictoors) == len(predictoor_data)
    for addr, original_predictoor in predictoor_data.items():
        loaded_predictoor = loaded_predictoors[addr]
        assert loaded_predictoor.accuracy == original_predictoor.accuracy
        assert (
            loaded_predictoor.prediction_count == original_predictoor.prediction_count
        )
        assert (
            loaded_predictoor.correct_prediction_count
            == original_predictoor.correct_prediction_count
        )


@enforce_types
def test_predictoorrewards(tmp_path):
    target_csv = """predictoor_addr,reward
0x0000000000000000000000000000000000000000,10.0
0x1000000000000000000000000000000000000000,20.0
0x2000000000000000000000000000000000000000,30.0
0x3000000000000000000000000000000000000000,40.0
0x4000000000000000000000000000000000000000,50.0"""

    # generate random rewards
    predictoor_rewards = {}
    for i in range(5):
        predictoor_rewards[f"0x{i}000000000000000000000000000000000000000"] = (i + 1) * 10.0

    csv_dir = str(tmp_path)
    csvs.savePredictoorRewards(predictoor_rewards, csv_dir)

    with open(csvs.predictoorRewardsFilename(csv_dir), "r") as loaded_data:
        data = loaded_data.read().strip()
        assert data == target_csv

    loaded_predictoor_rewards = csvs.loadPredictoorRewards(csv_dir)
    assert len(loaded_predictoor_rewards) == len(predictoor_rewards)

    # loaded rewards should be equal to originally created ones
    for addr, original_reward in predictoor_rewards.items():
        loaded_reward = loaded_predictoor_rewards[addr]
        assert loaded_reward == original_reward
