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
    print(f"Found {len(predictoor_contracts)} OPF predictoor contracts")
    tokens_per_contract = tokens_avail / len(predictoor_contracts)

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
            continue

        # Calculate rewards for each predictoor for this contract
        for pdr_address, predictoor in predictoors.items():
            revenue_contract = predictoor.get_prediction_summary(contract).total_revenue
            if revenue_contract < 0:
                # ignore negative revenues
                continue
            rewards[contract][pdr_address] = (
                revenue_contract / total_revenue_for_contract * tokens_per_contract
            )

    return rewards
