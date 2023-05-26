from typing import List, Dict
from enforce_typing import enforce_types
from util.constants import MIN_PREDICTIONS


class Prediction:
    @enforce_types
    def __init__(self, slot: int, payout: float, contract_addr: str):
        self.slot = slot
        self.payout = payout
        self.contract_addr = contract_addr

    @property
    def is_correct(self) -> bool:
        """
        Returns true if the prediction is correct, false otherwise.
        """
        # We assume that the prediction is wrong if the payout is 0.
        # Only predictions where the true value for their slot is submitted are being counted, so this is a safe assumption.
        return self.payout > 0

    @classmethod
    def from_query_result(cls, prediction_dict: Dict) -> "Prediction":
        """
        @description
            Creates a Prediction object from a dictionary returned by a subgraph query.
        @params
            prediction_dict: A dictionary containing the prediction data.
        @return
            A Prediction object.
        @raises
            ValueError: If the input dictionary is invalid.
        """
        try:
            contract_addr = prediction_dict["slot"]["predictContract"]
            slot = int(prediction_dict["slot"]["slot"])
            payout = float(prediction_dict["payout"])
        except (KeyError, TypeError, ValueError):
            raise ValueError("Invalid prediction dictionary")
        return cls(slot, payout, contract_addr)


class Predictoor:
    @enforce_types
    def __init__(self, address: str):
        self._predictions: List[Prediction] = []
        self.address = address

    @enforce_types
    def add_prediction(self, prediction: Prediction):
        """
        Adds a prediction to the list of predictions for this Predictoor.
        @params
            prediction (Prediction) -- The prediction to add.
        """
        self._predictions.append(prediction)

    def get_accuracy(self) -> float:
        """
        Returns the accuracy of this Predictoor, defined as the proportion of correct predictions out of all predictions made.
        @return
            accuracy (float) -- The accuracy of this Predictoor.
        """
        n_predictions = len(self._predictions)
        if n_predictions < MIN_PREDICTIONS:
            return 0
        n_correct = sum(1 for prediction in self._predictions if prediction.is_correct)
        return n_correct / n_predictions

    def get_prediction_count(self) -> int:
        return len(self._predictions)

    def get_correct_prediction_count(self) -> int:
        return sum(1 for p in self._predictions if p.is_correct())
