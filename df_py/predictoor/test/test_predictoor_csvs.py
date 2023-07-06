from enforce_typing import enforce_types

from df_py.predictoor import csvs
from df_py.predictoor.models import Prediction, Predictoor


@enforce_types
def test_predictoordata(tmp_path):
    predictoors = {}

    for i in range(10):
        address = f"0x{i:01x}0000000000000000000000000000000000000000"
        predictoor = Predictoor(address)
        for j in range(5):
            predictoor.add_prediction(
                Prediction(
                    i, j % 2 * 1.0, f"0x000000000000000000000000000000000000000{j}"
                )
            )
        predictoors[address] = predictoor

    csvs.save_predictoor_data_csv(predictoors, str(tmp_path))

    loaded_predictoors = csvs.load_predictoor_data_csv(str(tmp_path))
    assert len(loaded_predictoors) == len(predictoors)

    for original_predictoor in predictoors.values():
        addr = original_predictoor.address
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
def test_predictoor_rewards(tmp_path):
    # generate random rewards
    predictoor_rewards = {}
    for i in range(5):
        predictoor_rewards[f"0x{i}000000000000000000000000000000000000000"] = (
            i + 1
        ) * 10.0

    csv_dir = str(tmp_path)
    csvs.save_predictoor_rewards_csv(predictoor_rewards, csv_dir)

    loaded_predictoor_rewards = csvs.load_predictoor_rewards_csv(csv_dir)
    assert len(loaded_predictoor_rewards) == len(predictoor_rewards)

    # loaded rewards should be equal to originally created ones
    for addr, original_reward in predictoor_rewards.items():
        loaded_reward = loaded_predictoor_rewards[addr]
        assert loaded_reward == original_reward
