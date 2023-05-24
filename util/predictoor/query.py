from typing import Dict

from util.graphutil import submitQuery
from util.predictoor.models import Predictoor, Prediction


def queryPredictoors(st_block: int, end_block: int, chainID: int):
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
            predictPredictions(where: {block_gte:%s, block_lte:%s}, skip:%s, first:%s) {
                id,
                slot{
                    status,
                    predictContract
                    slot
                },
                user {
                    id
                }
                payout
                block
            }
        """ % (
            st_block,
            end_block,
            offset,
            chunk_size,
        )
        offset += chunk_size
        result = submitQuery(query, chainID)
        if "error" in result:
            raise AssertionError(result)

        predictions = result["data"]["predictPredictions"]
        if len(predictions) == 0:
            break

        for prediction in predictions:
            predictoor_addr = prediction["user"]["id"]
            contract_addr = prediction["slot"]["predictContract"]
            payout = float(prediction["payout"])
            slot = int(prediction["slot"]["slot"])

            # 0 - Pending
            # 1 - Paying
            # 2 - Canceled
            status = prediction["slot"]["status"]
            if status != 1:
                break

            # only count predictions if the round is Paying
            prediction = Prediction(slot, payout, contract_addr)
            predictoors.setdefault(predictoor_addr, Predictoor(predictoor_addr))
            predictoors[predictoor_addr].add_prediction(prediction)

    return predictoors
