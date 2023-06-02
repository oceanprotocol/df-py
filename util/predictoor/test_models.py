import pytest
from util.predictoor.models import Prediction, Predictoor


def test_prediction_init():
    prediction = Prediction(123, 1.23, "0x1")
    assert prediction.slot == 123
    assert prediction.payout == 1.23
    assert prediction.contract_addr == "0x1"


def test_prediction_is_correct():
    prediction = Prediction(123, 1.23, "0x1")
    assert prediction.is_correct
    prediction = Prediction(123, 0.0, "0x1")
    assert not prediction.is_correct


def test_prediction_from_query_result():
    prediction_dict = {
        "slot": {
            "predictContract": {"id": "0x1"},
            "slot": "123",
        },
        "payout": {"payout": "1.23"},
    }
    prediction = Prediction.from_query_result(prediction_dict)
    assert prediction.slot == 123
    assert prediction.payout == 1.23
    assert prediction.contract_addr == "0x1"
    with pytest.raises(ValueError):
        prediction_dict = {"slot": {"predictContract": "0x123"}, "payout": "invalid"}
        Prediction.from_query_result(prediction_dict)


@pytest.mark.parametrize(
    "predictions, expected_accuracy",
    [
        ([], 0),
        ([Prediction(5, 0.5, "0x123")], 1),
        (
            [
                Prediction(5, 0.0, "0x123"),
                Prediction(5, 0.5, "0x123"),
                Prediction(5, 0.5, "0x123"),
            ],
            2 / 3,
        ),
        ([Prediction(2, 1.0, "0x123") for _ in range(100)], 1),
        ([Prediction(2, 0.0, "0x123") for _ in range(100)], 0),
        (
            [Prediction(2, 1.0 if i % 2 == 0 else 0.0, "0x123") for i in range(100)],
            0.5,
        ),
    ],
)
def test_predictor_accuracy(predictions, expected_accuracy):
    predictoor = Predictoor("0x123")
    for prediction in predictions:
        predictoor.add_prediction(prediction)
    assert predictoor.accuracy == expected_accuracy
