import pytest
from util.predictoor.models import Prediction
from util.predictoor.models import Predictoor
from util.constants import MIN_PREDICTIONS


def test_prediction_init():
    prediction = Prediction(123, 1.23, "0x1")
    assert prediction.slot == 123
    assert prediction.payout == 1.23
    assert prediction.contract_addr == "0x1"


def test_prediction_is_correct():
    prediction = Prediction(123, 1.23, "0x1")
    assert prediction.is_correct is True
    prediction = Prediction(123, 0.0, "0x1")
    assert prediction.is_correct is False


def test_prediction_from_query_result():
    prediction_dict = {
        "slot": {
            "predictContract": "0x1",
            "slot": "123",
        },
        "payout": "1.23",
    }
    prediction = Prediction.from_query_result(prediction_dict)
    assert prediction.slot == 123
    assert prediction.payout == 1.23
    assert prediction.contract_addr == "0x1"
    with pytest.raises(ValueError):
        prediction_dict = {"slot": {"predictContract": "0x123"}, "payout": "invalid"}
        Prediction.from_query_result(prediction_dict)


def test_predictoor_get_accuracy():
    # accuracy is 0 if there are no predictions
    predictoor = Predictoor("0x123")
    assert predictoor.get_accuracy() == 0

    predictoor.add_prediction(Prediction(5, 0.5, "0x123"))
    assert predictoor.get_accuracy() == 1

    # accuracy is correctly calculated
    # all predictions correct
    predictoor = Predictoor("0x123")
    for i in range(0, MIN_PREDICTIONS):
        predictoor.add_prediction(Prediction(2, 1.0, "0x123"))
    assert predictoor.get_accuracy() == 1

    # all predictions wrong
    predictoor = Predictoor("0x123")
    for i in range(0, MIN_PREDICTIONS):
        predictoor.add_prediction(Prediction(2, 0.0, "0x123"))
    assert predictoor.get_accuracy() == 0

    # half of the predictions are correct
    predictoor = Predictoor("0x123")
    n_predictions = MIN_PREDICTIONS + MIN_PREDICTIONS % 2
    for i in range(0, n_predictions):
        if i % 2 == 0:
            predictoor.add_prediction(Prediction(2, 1.0, "0x123"))
        else:
            predictoor.add_prediction(Prediction(2, 0.0, "0x123"))
    assert predictoor.get_accuracy() == 0.5
