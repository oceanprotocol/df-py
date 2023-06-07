from typing import Dict, List

from enforce_typing import enforce_types


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
        # Only predictions where the true value for their slot is submitted
        # are being counted, so this is a safe assumption.
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
            contract_addr = prediction_dict["slot"]["predictContract"]["id"]
            slot = int(prediction_dict["slot"]["slot"])
            payout = float(prediction_dict["payout"]["payout"])
        except (KeyError, TypeError, ValueError) as exc:
            raise ValueError("Invalid prediction dictionary") from exc
        return cls(slot, payout, contract_addr)


class PredictoorBase:
    def __init__(
        self,
        address: str,
        prediction_count: int,
        correct_prediction_count: int,
        accuracy: float,
    ):
        self._address = address
        self._prediction_count = prediction_count
        self._correct_prediction_count = correct_prediction_count
        self._accuracy = accuracy

    @property
    def address(self):
        return self._address

    @property
    def prediction_count(self):
        return self._prediction_count

    @property
    def correct_prediction_count(self):
        return self._correct_prediction_count

    @property
    def accuracy(self):
        return self._accuracy


class Predictoor(PredictoorBase):
    @enforce_types
    def __init__(self, address: str):
        super().__init__(address, 0, 0, 0)
        self._predictions: List[Prediction] = []

    @property
    def accuracy(self) -> float:
        if self._prediction_count == 0:
            return 0
        return self._correct_prediction_count / self._prediction_count

    @enforce_types
    def add_prediction(self, prediction: Prediction):
        self._predictions.append(prediction)
        self._prediction_count += 1
        if prediction.is_correct:
            self._correct_prediction_count += 1
