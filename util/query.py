import json
from typing import Any, Dict, List, Tuple

import requests
import brownie
from enforce_typing import enforce_types

from util import networkutil, oceanutil
from util.blockrange import BlockRange
from util.constants import AQUARIUS_BASE_URL, BROWNIE_PROJECT as B, MAX_ALLOCATE
from util.graphutil import submitQuery
from util.tok import TokSet


class DataNFT:
    def __init__(
        self,
        nft_addr: str,
        chain_id: int,
        _symbol: str,
        basetoken_addr: str,
        volume: float,
    ):
        self.nft_addr = nft_addr
        self.did = oceanutil.calcDID(nft_addr, chain_id)
        self.chain_id = chain_id
        self.symbol = _symbol
        self.basetoken_addr = basetoken_addr
        self.volume = volume

    def __repr__(self):
        return f"{self.nft_addr} {self.chain_id} {self.name} {self.symbol}"


@enforce_types
def query_all(
    rng: BlockRange, chainID: int
) -> Tuple[Dict[str, Dict[str, float]], List[str], Dict[str, str], List[DataNFT]]:
    """
    @description
      Return nftvols, nftInfo for the input block range and chain.

    @return
      nftvols_at_chain -- dict of [basetoken_addr][nft_addr] : vol
      approved_token_addrs_at_chain -- list_of_addr
      symbols_at_chain -- dict of [basetoken_addr] : basetoken_symbol
      nftinfo -- list of DataNFT objects

    @notes
      A stake or nftvol value is in terms of basetoken (eg OCEAN, H2O).
      Basetoken symbols are full uppercase, addresses are full lowercase.
    """
    Vi_unfiltered, nftInfo = getNFTVolumes(rng.st, rng.fin, chainID)
    Vi = _filterOutPurgatory(Vi_unfiltered, chainID)

    if chainID != networkutil.DEV_CHAINID:
        # when not on dev chain:
        # filter out assets that are not on the market
        Vi = _filterOutNonMarketAssets(Vi, chainID)

    ASETi: TokSet = getApprovedTokens(chainID)
    Ai = ASETi.exportTokenAddrs()[chainID]
    SYMi = getSymbols(ASETi, chainID)
    return (Vi, Ai, SYMi, nftInfo)


@enforce_types
def getveBalances(rng: BlockRange, CHAINID: int) -> Dict[str, float]:
    """
    @description
      Return all ve balances

    @return
      veBalances -- dict of veBalances [LP_addr] : veBalance
    """
    MAX_TIME = 4 * 365 * 86400  # max lock time

    veBalances: Dict[str, float] = {}
    unixEpochTime = brownie.network.chain.time()
    n_blocks = rng.numBlocks()
    n_blocks_sampled = 0
    blocks = rng.getBlocks()
    print("getveBalances: begin")

    for block_i, block in enumerate(blocks):
        if (block_i % 50) == 0 or (block_i == n_blocks - 1):
            print(f"  {(block_i+1) / float(n_blocks) * 100.0:.1f}% done")
        chunk_size = 1000
        offset = 0
        while True:
            query = """
              {
                veOCEANs(first: %d, skip: %d,block:{number: %d}) {
                  id
                  lockedAmount
                  unlockTime
                  delegation {
                    id
                    amount
                  }
                  delegates {
                    id
                    amount
                  }
                }
              }
            """ % (
                chunk_size,
                offset,
                block,
            )

            result = submitQuery(query, CHAINID)
            if not "data" in result:
                raise Exception(f"No data in veOCEANs result: {result}")
            veOCEANs = result["data"]["veOCEANs"]

            if len(veOCEANs) == 0:
                # means there are no records left
                break

            for user in veOCEANs:
                timeLeft = (
                    float(user["unlockTime"]) - unixEpochTime
                )  # time left in seconds
                if timeLeft < 0:  # check if the lock has expired
                    continue

                # calculate the balance
                balance = float(user["lockedAmount"]) * timeLeft / MAX_TIME

                # calculate delegations
                ## calculate total amount going
                totalAmountGoing = 0.0
                for delegation in user["delegation"]:
                    totalAmountGoing += float(delegation["amount"])

                ## calculate total amount coming
                totalAmountComing = 0.0
                for delegate in user["delegates"]:
                    totalAmountComing += float(delegate["amount"])

                ## calculate total amount
                totalAmount = totalAmountComing - totalAmountGoing

                ## convert wei to OCEAN
                totalAmount = totalAmount / 1e18

                ## add to balance
                balance += totalAmount

                ## set user balance
                if user["id"] not in veBalances:
                    veBalances[user["id"]] = balance

                veBalances[user["id"]] = (balance + veBalances[user["id"]]) / 2

            ## increase offset
            offset += chunk_size
        n_blocks_sampled += 1

    assert n_blocks_sampled > 0

    print("getveBalances: done")

    return veBalances


@enforce_types
def getAllocations(
    rng: BlockRange, CHAINID: int
) -> Dict[int, Dict[str, Dict[str, float]]]:
    """
    @description
      Return all allocations.

    @return
      allocations -- dict of [chain_id][nft_addr][LP_addr]: percent
    """

    _allocations: Dict[int, Dict[str, Dict[str, float]]] = {}
    n_blocks = rng.numBlocks()
    n_blocks_sampled = 0
    blocks = rng.getBlocks()

    for block_i, block in enumerate(blocks):

        if (block_i % 50) == 0 or (block_i == n_blocks - 1):
            print(f"  {(block_i+1) / float(n_blocks) * 100.0:.1f}% done")

        offset = 0
        chunk_size = 1000
        while True:
            query = """
          {
            veAllocateUsers(first: %d, skip: %d, block:{number:%d}) {
              id
              veAllocation {
                id
                allocated
                chainId
                nftAddress
              }
            }
          }
          """ % (
                chunk_size,
                offset,
                block,
            )
            result = submitQuery(query, CHAINID)
            allocations = result["data"]["veAllocateUsers"]
            if len(allocations) == 0:
                # means there are no records left
                break

            for allocation in allocations:
                LP_addr = allocation["id"]
                for ve_allocation in allocation["veAllocation"]:
                    nft_addr = ve_allocation["nftAddress"]
                    chain_id = ve_allocation["chainId"]
                    allocated = float(ve_allocation["allocated"])
                    if chain_id not in _allocations:
                        _allocations[chain_id] = {}
                    if nft_addr not in _allocations[chain_id]:
                        _allocations[chain_id][nft_addr] = {}

                    percentage = allocated / MAX_ALLOCATE

                    if LP_addr not in _allocations[chain_id][nft_addr]:
                        _allocations[chain_id][nft_addr][LP_addr] = percentage

                    _allocations[chain_id][nft_addr][LP_addr] = (
                        percentage + _allocations[chain_id][nft_addr][LP_addr]
                    ) / 2

            offset += chunk_size
        n_blocks_sampled += 1

    assert n_blocks_sampled > 0

    return _allocations


def getNFTVolumes(
    st_block: int, end_block: int, chainID: int
) -> Tuple[Dict[str, Dict[str, float]], List[DataNFT]]:
    """
    @description
      Query the chain for datanft volumes within the given block range.

    @return
      nft_vols_at_chain -- dict of [basetoken_addr][nft_addr]:vol_amt
      NFTinfo -- list of DataNFT objects
    """
    print("getVolumes(): begin")

    NFTvols: Dict[str, Dict[str, float]] = {}
    NFTinfo_tmp: Dict[str, Dict[str, Dict[str, Any]]] = {}
    NFTinfo = []

    chunk_size = 1000  # max for subgraph = 1000
    offset = 0
    while True:
        query = """
        {
          orders(where: {block_gte:%s, block_lte:%s}, skip:%s, first:%s) {
            id,
            datatoken {
              id
              symbol
              nft {
                id
              }
            },
            lastPriceToken,
            lastPriceValue,
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
        result = submitQuery(query, chainID)
        new_orders = result["data"]["orders"]
        if new_orders == []:
            break
        for order in new_orders:
            lastPriceValue = float(order["lastPriceValue"])
            if lastPriceValue == 0:
                continue
            nft_addr = order["datatoken"]["nft"]["id"].lower()
            basetoken_addr = order["lastPriceToken"]

            if basetoken_addr not in NFTvols:
                NFTvols[basetoken_addr] = {}

            if nft_addr not in NFTvols[basetoken_addr]:
                NFTvols[basetoken_addr][nft_addr] = 0.0
            NFTvols[basetoken_addr][nft_addr] += lastPriceValue

            ### Store nft symbol for later use
            if not basetoken_addr in NFTinfo_tmp:
                NFTinfo_tmp[basetoken_addr] = {}

            if not nft_addr in NFTinfo_tmp[basetoken_addr]:
                NFTinfo_tmp[basetoken_addr][nft_addr] = {}

            NFTinfo_tmp[basetoken_addr][nft_addr]["symbol"] = order["datatoken"][
                "symbol"
            ]

    for base_addr in NFTinfo_tmp:
        for nft_addr in NFTinfo_tmp[base_addr]:
            datanft = DataNFT(
                nft_addr,
                chainID,
                NFTinfo_tmp[base_addr][nft_addr]["symbol"],
                base_addr,
                NFTvols[base_addr][nft_addr],
            )
            NFTinfo.append(datanft)

    print("getVolumes(): done")
    return NFTvols, NFTinfo


@enforce_types
def _filterOutPurgatory(nftvols: dict, chainID: int) -> dict:
    """
    @description
      Return nfts that aren't in purgatory

    @arguments
      nftvols: dict of [basetoken_addr][nft_addr]:vol_amt

    @return
      filtered_nftvols: list of [basetoken_addr][nft_addr]:vol_amt
    """
    bad_dids = _didsInPurgatory()
    filtered_nfts: Dict[str, Dict[str, float]] = {}
    for basetoken_addr in nftvols:
        for nft_addr in nftvols[basetoken_addr]:
            if oceanutil.calcDID(nft_addr, chainID) not in bad_dids:
                if basetoken_addr not in filtered_nfts:
                    filtered_nfts[basetoken_addr] = {}
                filtered_nfts[basetoken_addr][nft_addr] = nftvols[basetoken_addr][
                    nft_addr
                ]
    return filtered_nfts


@enforce_types
def _filterOutNonMarketAssets(nftvols: dict, chainID: int) -> dict:
    """
    @description
      Return nfts that belong to the Ocean marketplace

    @arguments
      nftvols: dict of [basetoken_addr][nft_addr]:vol_amt

    @return
      filtered_nftvols: list of [basetoken_addr][nft_addr]:vol_amt
    """
    filtered_nfts: Dict[str, Dict[str, float]] = {}
    didList = []

    for basetoken_addr in nftvols:
        for nft_addr in nftvols[basetoken_addr]:
            didList.append(oceanutil.calcDID(nft_addr, chainID))

    aquariusAssetNames = getAquariusAssetNames(didList)

    # Aquarius returns "" as the name for assets that aren't in the marketplace
    for basetoken_addr in nftvols:
        for nft_addr in nftvols[basetoken_addr]:
            did = oceanutil.calcDID(nft_addr, chainID)
            if aquariusAssetNames[did] != "":
                if basetoken_addr not in filtered_nfts:
                    filtered_nfts[basetoken_addr] = {}
                filtered_nfts[basetoken_addr][nft_addr] = nftvols[basetoken_addr][
                    nft_addr
                ]

    return filtered_nfts


@enforce_types
def _didsInPurgatory() -> List[str]:
    """
    @description
      Return dids of data assets that are in purgatory

    @return
      dids -- list of str
    """
    url = "https://raw.githubusercontent.com/oceanprotocol/list-purgatory/main/list-assets.json"
    resp = requests.get(url)

    # list of {'did' : 'did:op:6F7...', 'reason':'..'}
    data = json.loads(resp.text)

    dids = [item["did"] for item in data]
    return dids


@enforce_types
def getApprovedTokenAddrs(chainID: int) -> dict:
    """@return - approved_token_addrs_at_chain -- dict of [chainID] : list_of_addr"""
    tok_set = getApprovedTokens(chainID)
    d = tok_set.exportTokenAddrs()
    return d


@enforce_types
def getApprovedTokens(chainID: int) -> TokSet:
    """
    @description
      Return basetokens that are 'approved', ie eligible for data farming

    @return
      approved_tokens -- TokSet
    """
    query = "{ opcs { approvedTokens { id } } }"
    result = submitQuery(query, chainID)
    if len(result["data"]["opcs"][0]["approvedTokens"]) == 0:
        raise Exception(f"No approved tokens found in the chain {chainID}")
    # subgraph data: "approvedTokens": [ { "id": "address" } ]

    approved_tokens = TokSet()
    for x in result["data"]["opcs"][0]["approvedTokens"]:
        addr = x["id"].lower()
        symb = B.Simpletoken.at(addr).symbol().upper()
        approved_tokens.add(chainID, addr, symb)

    return approved_tokens


@enforce_types
def getSymbols(approved_tokens: TokSet, chainID: int) -> Dict[str, str]:
    """
    @description
      Return mapping of basetoken addr -> symbol for this chain

    @return
      symbols_at_chain -- dict of [basetoken_addr] : basetoken_symbol
    """
    return {
        tok.address: tok.symbol
        for tok in approved_tokens.toks
        if tok.chainID == chainID
    }


_ADDR_TO_SYMBOL = {}  # address : TOKEN_symbol


def symbol(addr: str):
    """Returns token symbol, given its address."""
    global _ADDR_TO_SYMBOL
    if addr not in _ADDR_TO_SYMBOL:
        _symbol = B.Simpletoken.at(addr).symbol()
        _symbol = _symbol.upper()  # follow lower-upper rules
        _ADDR_TO_SYMBOL[addr] = _symbol
    return _ADDR_TO_SYMBOL[addr]


@enforce_types
def getAquariusAssetNames(
    didList: List[str],
) -> Dict[str, str]:
    """
    @description
      Return mapping of did -> asset name

    @params
      didList -- array of dids

    @return
      did_to_asset_name -- dict of [did] : asset_name
    """

    # make a post request to Aquarius
    url = f"{AQUARIUS_BASE_URL}/api/aquarius/assets/names"

    headers = {"Content-Type": "application/json"}

    did_to_asset_name = {}

    BATCH_SIZE = 5000
    RETRY_ATTEMPTS = 3

    error_counter = 0
    # Send in 5k chunks
    for i in range(0, len(didList), BATCH_SIZE):
        # Aquarius expects "didList": ["did:op:...", ...]
        payload = json.dumps({"didList": didList[i : i + BATCH_SIZE]})

        try:
            resp = requests.post(url, data=payload, headers=headers)
            data = json.loads(resp.text)
            did_to_asset_name.update(data)
        # pylint: disable=broad-except
        except Exception as e:
            error_counter += 1
            i -= BATCH_SIZE
            if error_counter > RETRY_ATTEMPTS:
                # pylint: disable=line-too-long
                raise Exception(
                    f"Failed to get asset names from Aquarius after {RETRY_ATTEMPTS} attempts. Error: {e}"
                ) from e
        error_counter = 0

    # parse response

    return did_to_asset_name
