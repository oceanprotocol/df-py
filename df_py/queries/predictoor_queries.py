from typing import Dict, List, Optional

from enforce_typing import enforce_types
from web3 import Web3

from df_py.predictoor.models import PredictContract, Prediction, Predictoor
from df_py.web3util.constants import DEPLOYER_ADDRS
from df_py.queries.submit_query import submit_query
from df_py.web3util.networkutil import DEV_CHAINID


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


@enforce_types
def query_predictoor_feed_addrs(chainIDs: List[int]) -> Dict[int, List[str]]:
    """
    @return
      addrs -- dict of [chainID] : list of addr_of_predictoor_feed_nft

    @notes
      This will only return the prediction feeds that are owned by DEPLOYER_ADDRS, due to functionality of query_predictoor_contracts().
    """
    addrs: Dict[int, List[str]] = {chain_id: [] for chain_id in chainIDs}

    for chain_id in DEPLOYER_ADDRS.keys():
        addrs[chain_id] = query_predictoor_contracts(chain_id).keys()

    return addrs
