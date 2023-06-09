from typing import Dict, Union

from df_py.predictoor.models import Predictoor, PredictoorBase
from df_py.util.constants import MIN_PREDICTIONS


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


def calc_predictoor_rewards(
    predictoors: Dict[str, Union[PredictoorBase, Predictoor]], tokens_avail: float
) -> Dict[str, float]:
    # filter predictoors by min prediction count
    predictoors = filter_predictoors(predictoors)

    # reward calculation function
    tot_accuracy = sum([p.accuracy for p in predictoors.values()])
    if tot_accuracy == 0:
        return {}
    rewards = {
        k: v.accuracy / tot_accuracy * tokens_avail for k, v in predictoors.items()
    }
    return rewards
