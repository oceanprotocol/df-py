import pytest

from df_py.predictoor.models import PredictContract, Prediction, Predictoor


def test_prediction_init():
    prediction = Prediction(123, 1.23, 1.0, "0x1")
    assert prediction.slot == 123
    assert prediction.payout == 1.23
    assert prediction.contract_addr == "0x1"


def test_prediction_is_correct():
    prediction = Prediction(123, 1.23, 1.0, "0x1")
    assert prediction.is_correct
    prediction = Prediction(123, 0.0, 1.0, "0x1")
    assert not prediction.is_correct


def test_prediction_profit():
    prediction = Prediction(123, 10, 1.0, "0x1")
    assert prediction.revenue == 10

    prediction = Prediction(123, 0, 1.0, "0x1")
    assert prediction.revenue == -1


def test_prediction_from_query_result():
    prediction_dict = {
        "slot": {
            "predictContract": {"id": "0x1", "token": {"nft": {"id": "0x2"}}},
            "stake": "0.22352",
            "slot": "123",
        },
        "payout": {"payout": "1.23"},
    }
    prediction = Prediction.from_query_result(prediction_dict)
    assert prediction.slot == 123
    assert prediction.payout == 1.23
    assert prediction.stake == 0.22352
    assert prediction.revenue == prediction.payout
    assert prediction.contract_addr == "0x2"
    with pytest.raises(ValueError):
        prediction_dict = {"slot": {"predictContract": "0x123"}, "payout": "invalid"}
        Prediction.from_query_result(prediction_dict)


@pytest.mark.parametrize(
    "predictions, expected_accuracy",
    [
        ([], 0),
        ([Prediction(5, 0.5, 1.0, "0x123")], 1),
        (
            [
                Prediction(5, 0.0, 1.0, "0x123"),
                Prediction(5, 0.5, 1.0, "0x123"),
                Prediction(5, 0.5, 1.0, "0x123"),
            ],
            2 / 3,
        ),
        ([Prediction(2, 1.0, 1.0, "0x123") for _ in range(100)], 1),
        ([Prediction(2, 0.0, 1.0, "0x123") for _ in range(100)], 0),
        (
            [
                Prediction(2, 1.0 if i % 2 == 0 else 0.0, 1.0, "0x123")
                for i in range(100)
            ],
            0.5,
        ),
    ],
)
def test_predictor_accuracy(predictions, expected_accuracy):
    predictoor = Predictoor("0x123")
    for prediction in predictions:
        predictoor.add_prediction(prediction)
    assert predictoor.accuracy == expected_accuracy


def test_predict_contract():
    contract = PredictContract(
        chainid=1,
        address="0xContract1",
        name="Contract1",
        symbol="CTR1",
        blocks_per_epoch=100,
        blocks_per_subscription=10,
    )

    contract_dict = contract.to_dict()
    expected_dict = {
        "chainid": "1",
        "address": "0xcontract1",
        "name": "Contract1",
        "symbol": "CTR1",
        "blocks_per_epoch": "100",
        "blocks_per_subscription": "10",
    }
    assert contract_dict == expected_dict

    contract_from_dict = PredictContract.from_dict(contract_dict)

    assert contract_from_dict.chainid == contract.chainid
    assert contract_from_dict.address == contract.address
    assert contract_from_dict.name == contract.name
    assert contract_from_dict.symbol == contract.symbol
    assert contract_from_dict.blocks_per_epoch == contract.blocks_per_epoch
    assert (
        contract_from_dict.blocks_per_subscription == contract.blocks_per_subscription
    )
