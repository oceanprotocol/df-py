from typing import Dict, Union

from enforce_typing import enforce_types

from df_py.predictoor.models import Predictoor
from df_py.predictoor.queries import query_predictoor_contracts
from df_py.util.graphutil import wait_to_latest_block


@enforce_types
def calc_predictoor_rewards(
    predictoors: Dict[str, Predictoor], tokens_avail: Union[int, float], chain_id: int
) -> Dict[str, Dict[str, float]]:
    """
    Calculate rewards for predictoors based on their weekly payout.

    @arguments
    predictoors -- dict of [pdr_address] : Predictoor objects
        The predictoors to calculate rewards for.
    tokens_avail -- float
        The number of tokens available for distribution as rewards.

    @return
    rewards -- dict of [contract addr][predictoor addr]: float
        The calculated rewards for each predictoor per contract address.
    """
    MIN_REWARD = 1e-15
    tokens_avail = float(tokens_avail)

    wait_to_latest_block(chain_id)

    predictoor_contracts = query_predictoor_contracts(chain_id).keys()
    print("# of available contracts: ", len(predictoor_contracts))
    tokens_per_contract = tokens_avail / len(predictoor_contracts)
    print("Tokens per contract:", tokens_per_contract)

    # dict to store rewards per contract
    rewards: Dict[str, Dict[str, float]] = {
        contract: {} for contract in predictoor_contracts
    }

    # Loop through each contract and calculate the rewards for predictions
    # made for that specific contract
    for contract in predictoor_contracts:
        slots = []
        # Find the unique slots for the contract
        for predictoor in predictoors.values():
            slots_p = predictoor.slots_for_contract(contract)
            slots.extend(slots_p)

        unique_slots = set(slots)
        print(
            "Contract",
            contract,
            "has",
            len(unique_slots),
            "unique slots",
            "and",
            len(predictoors),
            "predictoors",
        )
        if len(unique_slots) == 0:
            print("No slots for contract", contract)
            continue

        # Calculate the rewards for each predictoor for the contract
        token_avail_per_slot = tokens_per_contract / len(unique_slots)

        # go over each slot, compare predictoors, and distribute rewards
        for slot in unique_slots:
            total_revenue_slot = 0.0
            for predictoor in predictoors.values():
                predictoor_summary = predictoor.get_prediction_summary(contract, slot)
                predictoor_revenue = predictoor_summary.total_revenue
                if predictoor_revenue > 0:
                    total_revenue_slot += predictoor_revenue

            for predictoor in predictoors.values():
                predictoor_summary = predictoor.get_prediction_summary(contract, slot)
                predictoor_revenue = predictoor_summary.total_revenue
                if total_revenue_slot <= 0:
                    continue
                reward = token_avail_per_slot * (
                    predictoor_revenue / total_revenue_slot
                )
                if contract not in rewards:
                    rewards[contract] = {}
                if predictoor.address not in rewards[contract]:
                    rewards[contract][predictoor.address] = 0
                rewards[contract][predictoor.address] += reward

        # filter out predictoors with rewards below MIN_REWARD
        for predictoor in predictoors.values():
            if contract in rewards and predictoor.address in rewards[contract]:
                if rewards[contract][predictoor.address] < MIN_REWARD:
                    del rewards[contract][predictoor.address]

    return rewards


def aggregate_predictoor_rewards(
    predictoor_rewards: Dict[str, Dict[str, float]]
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
