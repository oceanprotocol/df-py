from typing import Dict
from enforce_typing import enforce_types

from df_py.predictoor.models import Prediction, Predictoor, PredictContract
from df_py.util.constants import DEPLOYER_ADDRS
from df_py.util.graphutil import submit_query
from df_py.util.networkutil import DEV_CHAINID


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
            owner = contract["token"]["nft"]["owner"]
            if chain_id != DEV_CHAINID and owner["id"] not in DEPLOYER_ADDRS[chain_id]:
                continue

            nft_addr = contract["token"]["nft"]["id"]
            contract_obj = PredictContract(
                chain_id,
                nft_addr,
                contract["token"]["name"],
                contract["token"]["symbol"],
                contract["secondsPerEpoch"],
                contract["secondsPerSubscription"],
            )
            contracts_dict[nft_addr] = contract_obj
    return contracts_dict


@enforce_types
def query_predictoors(
    st_block: int, end_block: int, chainID: int
) -> Dict[str, Predictoor]:
    """
    @description
        Queries the predictPredictions GraphQL endpoint for a given
        range of blocks and chain ID, and returns a dictionary of
        Predictoor objects, where each Predictoor object represents
        a unique user who has made predictions during the given block range.

    @params
        st_block (int) -- The starting block number for the query.
        end_block (int) -- The ending block number for the query.
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
            predictPredictions(where: {block_gte:%s, block_lte:%s}, skip:%s, first:%s) {
                id,
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
                payout
                block
            }
        }
        """ % (
            st_block,
            end_block,
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
            owner = prediction_dict["slot"]["predictContract"]["token"]["nft"]["owner"]
            if chainID != DEV_CHAINID:
                if owner not in DEPLOYER_ADDRS[chainID]:
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
