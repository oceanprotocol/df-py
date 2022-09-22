# pylint: disable=logging-fstring-interpolation
from typing import Dict, Optional

from enforce_typing import enforce_types

from util.constants import BROWNIE_PROJECT as B
from util.base18 import toBase18
from util.logger import logger

MAX_BATCH_SIZE = 100
TRY_AGAIN = 3


@enforce_types
def dispense(
    rewards: Dict[str, float],
    dfrewards_addr: str,
    token_addr: str,
    from_account,
    batch_size: int = MAX_BATCH_SIZE,
    batch_number: Optional[int] = None,
):
    """
    @description
      Allocate rewards to LPs.

    @arguments
      rewards -- dict of [LP_addr]:TOKEN_amt (float, not wei)
        -- rewards for each LP
      dfrewards_addr -- address of dfrewards contract
      token_addr -- address of token we're allocating rewards with (eg OCEAN)
      from_account -- account doing the spending
      batch_size -- largest # LPs allocated per tx (due to EVM limits)
      batch_number -- specify the batch number to run dispense only for that batch.

    @return
      <<nothing, but updates the dfrewards contract on-chain>>
    """
    logger.info("dispense: begin")
    logger.info(f"  # addresses: {len(rewards)}")

    df_rewards = B.DFRewards.at(dfrewards_addr)
    TOK = B.Simpletoken.at(token_addr)
    logger.info(f"  Total amount: {sum(rewards.values())} {TOK.symbol()}")

    to_addrs = list(rewards.keys())
    values = [toBase18(rewards[to_addr]) for to_addr in to_addrs]

    N = len(rewards)
    sts = list(range(N))[::batch_size]  # send in batches to avoid gas issues

    if batch_number is not None:
        b_st = (batch_number - 1) * batch_size
        TOK.approve(
            df_rewards,
            sum(values[b_st : b_st + batch_size]),
            {"from": from_account},
        )
    else:
        TOK.approve(df_rewards, sum(values), {"from": from_account})

    logger.info(f"Total {len(sts)} batches")
    for i, st in enumerate(sts):
        if batch_number is not None and batch_number != i + 1:
            continue
        fin = st + batch_size
        done = False
        for z in range(TRY_AGAIN):
            try:
                # pylint: disable=line-too-long
                logger.info(
                    f"Allocating rewards Batch #{(i+1)}/{len(sts)}, {len(to_addrs[st:fin])} addresses {z}"
                )
                df_rewards.allocate(
                    to_addrs[st:fin],
                    values[st:fin],
                    TOK.address,
                    {"from": from_account},
                )
                done = True
                break
            # pylint: disable=broad-except
            except Exception as e:
                logger.critical(
                    f'An error occured "{e}" while allocating funds, trying again {z}'
                )
        if done is False:
            logger.critical(f"Could not allocate funds for batch {i+1}")
    logger.info("dispense: done")
