import csv
import os
from copy import copy
from typing import Any, Dict, List, Tuple

from enforce_typing import enforce_types
from web3.main import Web3

from df_py.util.csv_helpers import assert_is_eth_addr


@enforce_types
def save_challenge_data_csv(challenge_data: tuple, csv_dir: str):
    """
    @description
      Save challenge data csv.

    @arguments
      challenge_data -- tuple of (from_addrs, nft_addrs, nmses),
        all ordered with lowest nmse first
      csv_dir --
    """
    (from_addrs, nft_addrs, nmses) = challenge_data
    assert len(from_addrs) == len(nft_addrs) == len(nmses)
    assert sorted(nmses) == nmses

    assert os.path.exists(csv_dir), csv_dir
    csv_file = challenge_data_csv_filename(csv_dir)
    assert not os.path.exists(csv_file), csv_file

    with open(csv_file, "w") as f:
        writer = csv.writer(f)
        row = ["from_addr", "nft_addr", "nmse"]
        writer.writerow(row)
        for from_addr, nft_addr, nmse in zip(from_addrs, nft_addrs, nmses):
            assert_is_eth_addr(from_addr)
            assert_is_eth_addr(nft_addr)
            row = [
                from_addr.lower(),
                nft_addr.lower(),
                f"{nmse:.3e}",
            ]
            writer.writerow(row)

    print(f"Created {csv_file}")


@enforce_types
def load_challenge_data_csv(csv_dir: str) -> Tuple[List[str], List[str], list]:
    """
    @description
      Load challenge data csv

    @return
      challenge_data -- tuple of (from_addrs, nft_addrs, nmses),
        all ordered with lowest nmse first
    """
    csv_file = challenge_data_csv_filename(csv_dir)
    from_addrs, nft_addrs, nmses = [], [], []

    with open(csv_file, "r") as f:
        reader = csv.reader(f)
        for row_i, row in enumerate(reader):
            if row_i == 0:
                assert row == ["from_addr", "nft_addr", "nmse"]
                continue
            from_addr, nft_addr, nmse_s = row

            from_addr = from_addr.lower()
            nft_addr = nft_addr.lower()
            nmse = float(nmse_s)

            assert_is_eth_addr(from_addr)
            assert_is_eth_addr(nft_addr)

            from_addrs.append(from_addr)
            nft_addrs.append(nft_addr)
            nmses.append(nmse)

    assert nmses == sorted(nmses), "should be sorted by lowest-nmse first"

    print(f"Loaded {csv_file}")
    return (from_addrs, nft_addrs, nmses)


@enforce_types
def challenge_data_csv_filename(csv_dir: str) -> str:
    f = "challenge_data.csv"
    return os.path.join(csv_dir, f)


# ------------------------------- REWARDS -------------------------------


@enforce_types
def challenge_rewards_csv_filename(csv_dir):
    f = "challenge_rewards.csv"
    return os.path.join(csv_dir, f)


@enforce_types
def save_challenge_rewards_csv(challenge_rewards: List[Dict[str, Any]], csv_dir: str):
    """Saves the challenge rewards to a CSV file.
    @arguments
      - challenge_rewards: A list of dictionaries representing rewards for the challenge.
        Each dictionary contains the following keys:
        - winner_addr: The address of the winner.
        - OCEAN_amt: The amount of OCEAN tokens to be awarded to the winner.
      - csv_dir: The directory to save the CSV file.
    @return
      - The filename of the saved CSV file.
    """
    assert os.path.exists(csv_dir), csv_dir
    csv_file = challenge_rewards_csv_filename(csv_dir)
    assert not os.path.exists(csv_file), csv_file

    with open(csv_file, "w") as f:
        writer = csv.DictWriter(f, fieldnames=["winner_addr", "OCEAN_amt"])
        writer.writeheader()
        for row in challenge_rewards:
            writer.writerow(row)

    print(f"Created {csv_file}")

    return csv_file


@enforce_types
def load_challenge_rewards_csv(csv_dir: str) -> Dict[str, float]:
    """Loads the challenge rewards from a CSV file.
    Format of entries is a list of dicts, each dict with keys:
    - winner_addr: str, Ethereum address
    - OCEAN_amt: float, amount of OCEAN to award
    """
    csv_file = challenge_rewards_csv_filename(csv_dir)
    rewards = {}

    with open(csv_file, "r") as f:
        reader = csv.DictReader(f)
        for row in reader:
            rewards[Web3.to_checksum_address(row["winner_addr"])] = float(
                row["OCEAN_amt"]
            )

    print(f"Loaded {csv_file}")
    return rewards


def get_sample_challenge_data():
    return copy(
        (
            ["0xfrom1", "0xfrom2", "0xfrom3"],
            ["0xn1", "0xn2", "0xn3"],
            [0.42, 1.2, 2.3],
        )
    )


def get_sample_challenge_rewards():
    return copy(
        [
            {
                "winner_addr": "0xfrom1",
                "OCEAN_amt": 2500,
            },
            {
                "winner_addr": "0xfrom2",
                "OCEAN_amt": 1500,
            },
            {
                "winner_addr": "0xfrom3",
                "OCEAN_amt": 500,
            },
        ]
    )
