import os

# pylint: disable=logging-fstring-interpolation
from typing import Dict, Optional, Union

import brownie
from enforce_typing import enforce_types

from df_py.util.base18 import to_wei
from df_py.util.constants import BROWNIE_PROJECT as B
from df_py.util.logger import logger
from df_py.util.multisig import send_multisig_tx
from df_py.util.networkutil import chainIdToMultisigAddr

MAX_BATCH_SIZE = 500
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
    multisigaddr = None
    usemultisig = os.getenv("USE_MULTISIG", "false") == "true"
    if usemultisig:
        logger.info("multisig enabled")
        multisigaddr = chainIdToMultisigAddr(brownie.network.chain.id)
    df_rewards = B.DFRewards.at(dfrewards_addr)
    TOK = B.Simpletoken.at(token_addr)
    logger.info(f"  Total amount: {sum(rewards.values())} {TOK.symbol()}")
    to_addrs = list(rewards.keys())
    values = [to_wei(rewards[to_addr]) for to_addr in to_addrs]

    N = len(rewards)
    sts = list(range(N))[::batch_size]  # send in batches to avoid gas issues

    def approveAmt(amt):
        if usemultisig:
            data = TOK.approve.encode_input(df_rewards, amt)
            value = 0
            to = TOK.address
            # data = bytes.fromhex(data[2:])
            send_multisig_tx(multisigaddr, to, value, data)
            return
        TOK.approve(df_rewards, amt, {"from": from_account})

    if batch_number is not None:
        b_st = (batch_number - 1) * batch_size
        approveAmt(sum(values[b_st : b_st + batch_size]))
    else:
        approveAmt(sum(values))

    logger.info(f"Total {len(sts)} batches")
    for i, st in enumerate(sts):
        if batch_number is not None and batch_number != i + 1:
            continue
        fin = st + batch_size
        done = False
        for z in range(TRY_AGAIN):
            # pylint: disable=line-too-long
            logger.info(
                f"Allocating rewards Batch #{(i+1)}/{len(sts)}, {len(to_addrs[st:fin])} addresses {z}"
            )

            # if env use multisig
            if usemultisig:
                # get data of tx
                data = df_rewards.allocate.encode_input(
                    to_addrs[st:fin], values[st:fin], TOK.address
                )
                # value is 0
                value = 0
                to = df_rewards.address
                # convert data to bytes
                # data = bytes.fromhex(data[2:])

                send_multisig_tx(multisigaddr, to, value, data)
            else:
                df_rewards.allocate(
                    to_addrs[st:fin],
                    values[st:fin],
                    TOK.address,
                    {"from": from_account},
                )
            done = True
            break

        if done is False:
            logger.critical(f"Could not allocate funds for batch {i+1}")
    logger.info("dispense: done")


@enforce_types
def dispense_passive(ocean, feedistributor, amount: Union[float, int]):
    amount_wei = to_wei(amount)
    transfer_data = ocean.transfer.encode_input(feedistributor.address, amount_wei)

    checkpoint_total_supply_data = feedistributor.checkpoint_total_supply.encode_input()
    checkpoint_token_data = feedistributor.checkpoint_token.encode_input()

    multisig_addr = chainIdToMultisigAddr(brownie.network.chain.id)
    send_multisig_tx(multisig_addr, ocean.address, 0, transfer_data)

    for data in [checkpoint_total_supply_data, checkpoint_token_data]:
        send_multisig_tx(multisig_addr, feedistributor.address, 0, data)
