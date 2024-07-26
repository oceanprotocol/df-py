from typing import Dict, Optional

from enforce_typing import enforce_types
from web3 import Web3

from df_py.predictoor.models import PredictContract, Prediction, Predictoor
from df_py.util.constants import DEPLOYER_ADDRS
from df_py.util.graphutil import submit_query
from df_py.util.networkutil import DEV_CHAINID

WHITELIST_FEEDS_MAINNET = [
    "0x18f54cc21b7a2fdd011bea06bba7801b280e3151",
    "0x2d8e2267779d27c2b3ed5408408ff15d9f3a3152",
    "0x30f1c55e72fe105e4a1fbecdff3145fc14177695",
    "0x31fabe1fc9887af45b77c7d1e13c5133444ebfbd",
    "0x3fb744c3702ff2237fc65f261046ead36656f3bc",
    "0x55c6c33514f80b51a1f1b63c8ba229feb132cedb",
    "0x74a61f733bd9a2ce40d2e39738fe4912925c06dd",
    "0x8165caab33131a4ddbf7dc79f0a8a4920b0b2553",
    "0x93f9d558ccde9ea371a20d36bd3ba58c7218b48f",
    "0x9c4a2406e5aa0f908d6e816e5318b9fc8a507e1f",
    "0xa2d9dbbdf21c30bb3e63d16ba75f644ac11a0cf0",
    "0xaa6515c138183303b89b98aea756b54f711710c5",
    "0xb1c55346023dee4d8b0d7b10049f0c8854823766",
    "0xbe09c6e3f2341a79f74898b8d68c4b5818a2d434",
    "0xd41ffee162905b45b65fa6b6e4468599f0490065",
    "0xd49cbfd694f4556c00023ddd3559c36af3ae0a80",
    "0xe66421fd29fc2d27d0724f161f01b8cbdcd69690",
    "0xf28c94c55d8c5e1d70ca3a82744225a4f7570b30",
    "0xf8c34175fc1f1d373ec67c4fd1f1ce57c69c3fb3",
    "0xfa69b2c1224cebb3b6a36fb5b8c3c419afab08dd",
]

@enforce_types
def key_to_725(key: str):
    key725 = Web3.keccak(key.encode("utf-8")).hex()
    return key725


@enforce_types
def value_to_725(value: str):
    value725 = Web3.to_hex(text=value)
    return value725


@enforce_types
def value_from_725(value725) -> str:
    value = Web3.to_text(hexstr=value725)
    return value


@enforce_types
def info_from_725(info725_list: list) -> Dict[str, Optional[str]]:
    """
    @arguments
      info725_list -- eg [{"key":encoded("pair"), "value":encoded("ETH/USDT")},
                          {"key":encoded("timeframe"), "value":encoded("5m") },
                           ... ]
    @return
      info_dict -- e.g. {"pair": "ETH/USDT",
                         "timeframe": "5m",
                          ... }
    """
    target_keys = ["pair", "timeframe", "source", "base", "quote"]
    info_dict: Dict[str, Optional[str]] = {}
    for key in target_keys:
        info_dict[key] = None
        for item725 in info725_list:
            key725, value725 = item725["key"], item725["value"]
            if key725 == key_to_725(key):
                value = value_from_725(value725)
                info_dict[key] = value
                break

    return info_dict


@enforce_types
def query_predictoor_contracts(chain_id: int) -> Dict[str, PredictContract]:
    """
    @description
        Queries the predictContracts for a given chain ID,
        and returns a dictionary of PredictContract objects.

    @params
        chain_id (int) -- The ID of the chain to query.

    @return
        contracts_dict -- A dictionary mapping contract address to
                          PredictContract objects
    @raises
        AssertionError: If the result of the query contains an error.

    @notes
        This will only return the prediction feeds that are owned by DEPLOYER_ADDRS
    """

    chunk_size = 1000
    offset = 0
    contracts_dict = {}

    while True:
        query = """
        {
            predictContracts(skip:%s, first:%s){
                id
                token {
                    id
                    name
                    symbol
                    nft {
                        id
                        owner {
                            id
                        }
                        nftData {
                            key
                            value
                        }
                    }
                }
                secondsPerEpoch
                secondsPerSubscription
                truevalSubmitTimeout
            }
        }
        """ % (
            offset,
            chunk_size,
        )
        offset += chunk_size
        result = submit_query(query, chain_id)
        if "error" in result:
            raise AssertionError(result)
        if "data" not in result:
            raise AssertionError(result)
        predictoor_contracts = result["data"]["predictContracts"]
        if len(predictoor_contracts) == 0:
            break
        for contract in predictoor_contracts:
            if contract["id"] not in WHITELIST_FEEDS_MAINNET:
                owner = contract["token"]["nft"]["owner"]["id"]
                if chain_id != DEV_CHAINID and owner not in DEPLOYER_ADDRS[chain_id]:
                    continue

            nft_addr = contract["id"]
            pair = contract["token"]["name"].replace("/", "-")
            timeframe = "5m" if int(contract["secondsPerEpoch"]) == 300 else "1h"
            source = "binance"

            asset_name = f"{pair}-{source}-{timeframe}"

            contract_obj = PredictContract(
                chain_id,
                nft_addr,
                asset_name,
                contract["token"]["symbol"],
                contract["secondsPerEpoch"],
                contract["secondsPerSubscription"],
            )
            contracts_dict[nft_addr] = contract_obj

    print(contracts_dict)
    return contracts_dict


@enforce_types
def query_predictoors(st_ts: int, end_ts: int, chainID: int) -> Dict[str, Predictoor]:
    """
    @description
        Queries the predictPredictions GraphQL endpoint for a given
        range of blocks and chain ID, and returns a dictionary of
        Predictoor objects, where each Predictoor object represents
        a unique user who has made predictions during the given block range.

    @params
        st_ts (int) -- The start timestamp of the query.
        end_ts (int) -- The end timestamp of the query.
        chainID (int) -- The ID of the chain to query.

    @return
        predictoors -- A dictionary of address to Predictoor objects

    @raises
        AssertionError: If the result of the query contains an error.
    """
    predictoors: Dict[str, Predictoor] = {}

    chunk_size = 1000
    offset = 0

    while True:
        # pylint: disable=line-too-long
        query = """
        {
            predictPredictions(where: {slot_: {slot_gt: %s, slot_lte: %s, status: Paying}, payout_not: null}, skip:%s, first:%s) {
                id,
                stake,
                slot{
                    status,
                    predictContract {
                        id
                        token {
                            nft {
                                id
                                owner {
                                    id
                                }
                            }
                        }
                    }
                    slot
                },
                user {
                    id
                }
                payout {
                    id
                    payout
                }
                block
            }
        }
        """ % (
            st_ts,
            end_ts,
            offset,
            chunk_size,
        )

        offset += chunk_size
        result = submit_query(query, chainID)

        if "error" in result:
            raise AssertionError(result)
        if "data" not in result:
            raise AssertionError(result)

        predictions = result["data"]["predictPredictions"]
        print(len(predictoors))
        if len(predictions) == 0:
            break

        for prediction_dict in predictions:
            if prediction_dict["slot"]["predictContract"]["id"] not in WHITELIST_FEEDS_MAINNET:
                owner = prediction_dict["slot"]["predictContract"]["token"]["nft"]["owner"][
                    "id"
                ]
                if chainID != DEV_CHAINID:
                    if owner not in DEPLOYER_ADDRS[chainID]:
                        print("noowner", owner, chainID, DEPLOYER_ADDRS)
                        continue
            predictoor_addr = prediction_dict["user"]["id"]

            # 0 - Pending
            # 1 - Paying
            # 2 - Canceled
            status = prediction_dict["slot"]["status"]
            if status != "Paying":
                continue

            prediction = Prediction.from_query_result(prediction_dict)
            predictoors.setdefault(predictoor_addr, Predictoor(predictoor_addr))
            predictoors[predictoor_addr].add_prediction(prediction)

    return predictoors
