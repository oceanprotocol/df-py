import os
import brownie

# pylint: disable=logging-fstring-interpolation
from typing import Dict, Optional

from enforce_typing import enforce_types

from util.constants import BROWNIE_PROJECT as B
from util.base18 import toBase18
from util.logger import logger
from util.multisig import send_multisig_tx

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
    nonce = 0
    multisigaddr = None
    usemultisig = os.getenv("USE_MULTISIG", "false") == "true"
    if usemultisig:
        logger.info("multisig enabled")
        multisigaddr = "0xd701c6F346a6D99c44cc07E9E9E681B67184BF34"
        nonce = brownie.network.web3.eth.getTransactionCount(multisigaddr) + 1
    nonce = 0
    df_rewards = B.DFRewards.at(dfrewards_addr)
    TOK = B.Simpletoken.at(token_addr)
    logger.info(f"  Total amount: {sum(rewards.values())} {TOK.symbol()}")

    to_addrs = list(rewards.keys())
    values = [toBase18(rewards[to_addr]) for to_addr in to_addrs]

    N = len(rewards)
    sts = list(range(N))[::batch_size]  # send in batches to avoid gas issues

    def approveAmt(amt, nonce):
        if usemultisig:
            data = TOK.approve.encode_input(df_rewards, amt)
            value = 0
            to = TOK.address
            # data = bytes.fromhex(data[2:])
            send_multisig_tx(multisigaddr, to, value, data)
            return nonce + 1
        TOK.approve(df_rewards, amt, {"from": from_account})
        return 0

    if batch_number is not None:
        b_st = (batch_number - 1) * batch_size
        nonce = approveAmt(sum(values[b_st : b_st + batch_size]), nonce)
    else:
        nonce = approveAmt(sum(values), nonce)

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
                nonce += 1
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
