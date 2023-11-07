from typing import Dict, Union

from enforce_typing import enforce_types

from df_py.predictoor.models import Predictoor
from df_py.predictoor.queries import query_predictoor_contracts


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
    tokens_avail = float(tokens_avail)

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
        total_revenue_for_contract = 0
        for p in predictoors.values():
            summary = p.get_prediction_summary(contract)
            total_revenue_for_contract += max(
                summary.total_revenue, 0
            )  # ignore negative values

        # If total revenue for this contract is 0, no rewards are distributed
        if total_revenue_for_contract == 0:
            print("Total revenue for contract: ", contract, " was zero")
            continue

        # Calculate rewards for each predictoor for this contract
        for pdr_address, predictoor in predictoors.items():
            revenue_contract = predictoor.get_prediction_summary(contract).total_revenue
            if revenue_contract <= 0:
                # ignore negative revenues
                continue
            rewards[contract][pdr_address] = (
                revenue_contract / total_revenue_for_contract * tokens_per_contract
            )

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
