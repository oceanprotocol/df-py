from typing import Dict, Union

from enforce_typing import enforce_types

from df_py.predictoor.models import Predictoor, PredictoorBase
from df_py.predictoor.queries import query_predictoor_contracts
from df_py.util.constants import MIN_PREDICTIONS


@enforce_types
def filter_predictoors(
    predictoors: Dict[str, Union[PredictoorBase, Predictoor]]
) -> Dict[str, Union[PredictoorBase, Predictoor]]:
    """
    @description
    Filter away predictoors that have insufficient # predictions

    @arguments
    unfiltered predictoors -- dict of [pdr_address] : Predictoor

    @return
    filtered predictors -- dict of dict of [pdr_address] : Predictoor
    """
    return {
        k: v for k, v in predictoors.items() if v.prediction_count >= MIN_PREDICTIONS
    }


@enforce_types
def calc_predictoor_rewards(
    predictoors: Dict[str, Predictoor], tokens_avail: Union[int, float], chain_id: int
) -> Dict[str, Dict[str, float]]:
    """
    Calculate rewards for predictoors based on their accuracy and available tokens.

    @arguments
    predictoors -- dict of [pdr_address] : Predictoor objects
        The predictoors to calculate rewards for.
    tokens_avail -- float
        The number of tokens available for distribution as rewards.

    @return
    rewards -- dict of [contract addr][predictoor addr]: reward
        The calculated rewards for each predictoor per contract address.
    """

    predictoor_contracts = query_predictoor_contracts(chain_id)
    tokens_per_contract = tokens_avail / len(predictoor_contracts)

    # filter predictoors by min prediction count
    predictoors = filter_predictoors(predictoors)

    # dict to store rewards per contract
    rewards: Dict[str, Dict[str, float]] = {
        contract: {} for contract in predictoor_contracts
    }

    # Loop through each contract and calculate the rewards for predictions
    # made for that specific contract
    for contract in predictoor_contracts:
        total_accuracy_per_contract = sum(
            [
                p.get_prediction_summary(contract).accuracy
                for p in predictoors.values()
            ]
        )

        # If total accuracy for this contract is 0, no rewards are distributed
        if total_accuracy_per_contract == 0:
            continue

        # Calculate rewards for each predictoor for this contract
        for pdr_address, predictoor in predictoors.items():
            predictoor_summaries = predictoor.prediction_summaries
            if contract in predictoor_summaries:
                accuracy = predictoor_summaries[contract].accuracy
                rewards[contract][pdr_address] = (
                    accuracy / total_accuracy_per_contract * tokens_per_contract
                )

    return rewards
