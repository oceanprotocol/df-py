import csv
import os
from typing import List, Tuple

from enforce_typing import enforce_types

from df_py.util.csv_helpers import assertIsEthAddr


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
            assertIsEthAddr(from_addr)
            assertIsEthAddr(nft_addr)
            row = [
                from_addr.lower(),
                nft_addr.lower(),
                f"{nmse:.3e}",
            ]
            writer.writerow(row)

    print(f"Created {csv_file}")


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

            assertIsEthAddr(from_addr)
            assertIsEthAddr(nft_addr)

            from_addrs.append(from_addr)
            nft_addrs.append(nft_addr)
            nmses.append(nmse)
    assert nmses == sorted(nmses), "should be sorted by lowest-nmse first"

    print(f"Loaded {csv_file}")
    return (from_addrs, nft_addrs, nmses)


@enforce_types
def challenge_data_csv_filename(csv_dir: str) -> str:
    f = "challenge.csv"
    return os.path.join(csv_dir, f)
