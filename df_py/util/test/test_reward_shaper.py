from enforce_typing import enforce_types

from df_py.util.reward_shaper import RewardShaper

C1, C2, C3 = 7, 137, 1285  # chainIDs
LP1, LP2, LP3 = "0xlp1_addr", "0xlp2_addr", "0xlp3_addr"


@enforce_types
def test_flatten_rewards():
    rewards = {
        C1: {
            LP1: 100.0,
            LP2: 200.0,
        },
        C2: {
            LP1: 300.0,
        },
        C3: {
            LP1: 500.0,
            LP2: 600.0,
            LP3: 700.0,
        },
    }

    flat_rewards = RewardShaper.flatten(rewards)
    assert flat_rewards == {
        LP1: 100.0 + 300.0 + 500.0,
        LP2: 200.0 + 600.0,
        LP3: 700.0,
    }


@enforce_types
def test_merge_rewards():
    # Test case 1: Merge two reward dictionaries with no common keys
    dict1 = {"A": 10, "B": 20}
    dict2 = {"C": 30, "D": 40}
    expected_output = {"A": 10, "B": 20, "C": 30, "D": 40}
    assert RewardShaper.merge(dict1, dict2) == expected_output

    # Test case 2: Merge two reward dictionaries with common keys
    dict1 = {"A": 10, "B": 20}
    dict2 = {"B": 30, "C": 40}
    expected_output = {"A": 10, "B": 50, "C": 40}
    assert RewardShaper.merge(dict1, dict2) == expected_output

    # Test case 3: Merge three reward dictionaries with common keys
    dict1 = {"A": 10, "B": 20}
    dict2 = {"B": 30, "C": 40}
    dict3 = {"A": 50, "C": 60}
    expected_output = {"A": 60, "B": 50, "C": 100}
    assert RewardShaper.merge(dict1, dict2, dict3) == expected_output

    # Test case 4: Merge empty reward dictionary
    dict1 = {"A": 10, "B": 20}
    dict2 = {}
    expected_output = {"A": 10, "B": 20}
    assert RewardShaper.merge(dict1, dict2) == expected_output

    # Test case 5: Merge no reward dictionaries
    expected_output = {}
    assert RewardShaper.merge() == expected_output
