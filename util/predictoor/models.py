from typing import Dict
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
    def from_query_result(cls, prediction: Dict) -> "Prediction":
        contract_addr = prediction["slot"]["predictContract"]
        slot = int(prediction["slot"]["slot"])
        payout = float(prediction["payout"])
        return cls(slot, payout, contract_addr)


class Predictoor:
    @enforce_types
    def __init__(self, address: str):
        self.predictions: Dict[str, Prediction] = []
        self.address = address

    @enforce_types
    def add_prediction(self, prediction: Prediction):
        """
        Adds a prediction to the list of predictions for this Predictoor.
        @params
            prediction (Prediction) -- The prediction to add.
        """
        self.predictions.append(prediction)

    def get_accuracy(self) -> float:
        """
        Returns the accuracy of this Predictoor, defined as the proportion of correct predictions out of all predictions made.
        @return
            accuracy (float) -- The accuracy of this Predictoor.
        """
        n_predictions = len(self.predictions)
        if n_predictions < MIN_PREDICTIONS:
            return 0
        n_correct = sum(1 for prediction in self.predictions if prediction.is_correct)
        return n_correct / n_predictions
