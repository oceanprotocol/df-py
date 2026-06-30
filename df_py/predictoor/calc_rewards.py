from typing import Dict, Union

from enforce_typing import enforce_types

from df_py.predictoor.models import Predictoor
from df_py.predictoor.queries import query_predictoor_contracts
from df_py.util.graphutil import wait_to_latest_block

WEEK_SECONDS = 7 * 24 * 60 * 60


@enforce_types
def calc_predictoor_rewards(
    predictoors: Dict[str, Predictoor], tokens_avail: Union[int, float], chain_id: int
) -> Dict[str, Dict[str, float]]:
    """
    Calculate rewards for predictoors, distributed per epoch (slot).

    The budget is split in three stages:
      1. equally across prediction feeds (contracts),
      2. equally across all possible weekly epochs (slots) for that feed,
      3. within each epoch, proportionally to each predictoor's positive
         profit (payout - stake) for that epoch.

    Splitting by epoch first bounds how much a single position can capture:
    one large prediction in one epoch can win at most that epoch's small
    slice of the budget, not the whole weekly feed budget. This makes
    "both-siding" across unlinkable wallets far less profitable, since the
    manufactured-profit wallet can only ever drain a per-epoch budget.

    @arguments
    predictoors -- dict of [pdr_address] : Predictoor objects
        The predictoors to calculate rewards for.
    tokens_avail -- float
        The number of tokens available for distribution as rewards.
    chain_id -- int
        The chain to query the available feeds (contracts) from.

    @return
    rewards -- dict of [contract addr][predictoor addr]: float
        The calculated rewards for each predictoor per contract address,
        aggregated across all epochs of that contract.
    """
    MIN_REWARD = 1e-15
    tokens_avail = float(tokens_avail)

    wait_to_latest_block(chain_id)

    predictoor_contracts = query_predictoor_contracts(chain_id)
    print("# of available contracts: ", len(predictoor_contracts))
    tokens_per_contract = tokens_avail / len(predictoor_contracts)
    print("Tokens per contract:", tokens_per_contract)

    # dict to store rewards per contract
    rewards: Dict[str, Dict[str, float]] = {
        contract: {} for contract in predictoor_contracts
    }

    for contract, contract_obj in predictoor_contracts.items():
        # Build per-epoch profits for this contract:
        #   epoch_profits[slot][pdr_address] = summed profit for that epoch
        epoch_profits: Dict[int, Dict[str, float]] = {}
        for pdr_address, predictoor in predictoors.items():
            for prediction in predictoor._predictions:
                if prediction.contract_addr != contract:
                    continue
                slot_profits = epoch_profits.setdefault(prediction.slot, {})
                slot_profits[pdr_address] = (
                    slot_profits.get(pdr_address, 0.0) + prediction.revenue
                )

        seconds_per_epoch = contract_obj.blocks_per_epoch
        num_epochs = int(WEEK_SECONDS / seconds_per_epoch)
        if num_epochs == 0:
            print("No epochs for contract: ", contract)
            continue

        # Each epoch gets an equal slice of this contract's budget.
        epoch_budget = tokens_per_contract / num_epochs

        for slot_profits in epoch_profits.values():
            total_positive = sum(max(p, 0.0) for p in slot_profits.values())

            # If nobody profited this epoch, its budget is not distributed.
            if total_positive == 0:
                continue

            for pdr_address, profit in slot_profits.items():
                if profit <= 0:
                    # ignore non-positive (losing) profits
                    continue
                reward_amt = profit / total_positive * epoch_budget
                rewards[contract][pdr_address] = (
                    rewards[contract].get(pdr_address, 0.0) + reward_amt
                )

        # drop dust amounts
        rewards[contract] = {
            addr: amt for addr, amt in rewards[contract].items() if amt >= MIN_REWARD
        }

    return rewards


def aggregate_predictoor_rewards(
    predictoor_rewards: Dict[str, Dict[str, float]],
) -> Dict[str, float]:
    # Aggregate total reward per predictor address
    aggregated_rewards: Dict[str, float] = {}
    for _, rewards in predictoor_rewards.items():
        for predictor_addr, reward_amount in rewards.items():
            if predictor_addr in aggregated_rewards:
                aggregated_rewards[predictor_addr] += reward_amount
            else:
                aggregated_rewards[predictor_addr] = reward_amount
    return aggregated_rewards
