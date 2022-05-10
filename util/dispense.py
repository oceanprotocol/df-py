import csv
from enforce_typing import enforce_types
from typing import Dict
import os

from util.constants import BROWNIE_PROJECT as B
from util.base18 import fromBase18, toBase18

BATCH_SIZE = 100


@enforce_types
def dispense(
    rewards: Dict[str, float],
    airdrop_addr: str,
    from_account,
    batch_size: int = BATCH_SIZE,
):
    """
    @arguments
      rewards -- dict of [LP_addr]:OCEAN_float (not wei), from csv
      airdrop_addr -- address of airdrop contract
      ..
    """
    print("dispense: begin")
    print(f"  # addresses: {len(rewards)}")

    airdrop = B.Airdrop.at(airdrop_addr)
    TOK = B.Simpletoken.at(airdrop.getToken())
    print(f"  Total amount: {sum(rewards.values())} {TOK.symbol()}")

    to_addrs = list(rewards.keys())
    values = [toBase18(rewards[to_addr]) for to_addr in to_addrs]

    TOK.approve(airdrop, sum(values), {"from": from_account})

    N = len(rewards)
    sts = list(range(N))[::batch_size]  # send in batches to avoid gas issues
    for i, st in enumerate(sts):
        fin = st + batch_size
        print(f"  Batch #{(i+1)}/{len(sts)}, {len(to_addrs[st:fin])} addresses")
        airdrop.allocate(to_addrs[st:fin], values[st:fin], {"from": from_account})
    print("dispense: done")
