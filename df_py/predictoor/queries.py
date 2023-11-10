from typing import Dict, Optional

from enforce_typing import enforce_types
from web3 import Web3

from df_py.predictoor.models import PredictContract, Prediction, Predictoor
from df_py.util.constants import DEPLOYER_ADDRS
from df_py.util.graphutil import submit_query
from df_py.util.networkutil import DEV_CHAINID


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
            owner = contract["token"]["nft"]["owner"]["id"]
            if chain_id != DEV_CHAINID and owner not in DEPLOYER_ADDRS[chain_id]:
                continue

            nft_addr = contract["token"]["nft"]["id"]
            info725 = contract["token"]["nft"]["nftData"]
            info = info_from_725(info725)
            pair = info["pair"]
            timeframe = info["timeframe"]
            source = info["source"]

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
        if len(predictions) == 0:
            break

        for prediction_dict in predictions:
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
