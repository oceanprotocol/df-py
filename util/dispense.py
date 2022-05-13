import csv
from enforce_typing import enforce_types
from typing import Dict
import os

from util.constants import BROWNIE_PROJECT as B
from util.base18 import fromBase18, toBase18

MAX_BATCH_SIZE = 100


@enforce_types
def dispense(
    rewards_at_chain: Dict[str, float],
    airdrop_addr: str,
    token_addr: str,
    from_account,
    batch_size: int = MAX_BATCH_SIZE,
):
    """
    @description
      Allocate rewards to LPs.

    @arguments
      rewards_at_chain -- dict of [LP_addr]:TOKEN_amt (float, not wei)
        -- rewards for each LP on this chain
      airdrop_addr -- address of airdrop contract
      token_addr -- address of token we're allocating rewards with (eg OCEAN)
      from_account -- account doing the spending
      batch_size -- largest # LPs allocated per tx (due to EVM limits)

    @return
      <<nothing, but updates the airdrop contract on-chain>>
    """
    rewards = rewards_at_chain
    print("dispense: begin")
    print(f"  # addresses: {len(rewards)}")

    df_rewards = B.DFRewards.at(airdrop_addr)
    TOK = B.Simpletoken.at(token_addr)
    print(f"  Total amount: {sum(rewards.values())} {TOK.symbol()}")

    to_addrs = list(rewards.keys())
    values = [toBase18(rewards[to_addr]) for to_addr in to_addrs]

    TOK.approve(df_rewards, sum(values), {"from": from_account})

    N = len(rewards)
    sts = list(range(N))[::batch_size]  # send in batches to avoid gas issues
    for i, st in enumerate(sts):
        fin = st + batch_size
        print(f"  Batch #{(i+1)}/{len(sts)}, {len(to_addrs[st:fin])} addresses")
        df_rewards.allocate(
            to_addrs[st:fin], values[st:fin], TOK.address, {"from": from_account}
        )
    print("dispense: done")
