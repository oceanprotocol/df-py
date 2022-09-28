import json
from typing import Dict, List, Tuple

import requests
import brownie
from enforce_typing import enforce_types

from util import networkutil, oceanutil
from util.blockrange import BlockRange
from util.constants import (
    AQUARIUS_BASE_URL,
    BROWNIE_PROJECT as B,
    MAX_ALLOCATE,
)
from util.graphutil import submitQuery
from util.tok import TokSet
from util.base18 import fromBase18


class DataNFT:
    def __init__(
        self,
        nft_addr: str,
        chain_id: int,
        _symbol: str,
    ):
        self.nft_addr = nft_addr
        self.did = oceanutil.calcDID(nft_addr, chain_id)
        self.chain_id = chain_id
        self.symbol = _symbol

    def __repr__(self):
        return f"{self.nft_addr} {self.chain_id} {self.name} {self.symbol}"


@enforce_types
def query_all(
    rng: BlockRange, chainID: int
) -> Tuple[Dict[str, Dict[str, float]], List[str], Dict[str, str]]:
    """
    @description
      Return nftvols for the input block range and chain.

    @return
      nftvols_at_chain -- dict of [basetoken_addr][nft_addr] : vol
      approved_token_addrs_at_chain -- list_of_addr
      symbols_at_chain -- dict of [basetoken_addr] : basetoken_symbol

    @notes
      A stake or nftvol value is in terms of basetoken (eg OCEAN, H2O).
      Basetoken symbols are full uppercase, addresses are full lowercase.
    """
    Vi_unfiltered = getNFTVolumes(rng.st, rng.fin, chainID)
    Vi = _filterNftvols(Vi_unfiltered, chainID)

    ASETi: TokSet = getApprovedTokens(chainID)
    Ai = ASETi.exportTokenAddrs()[chainID]
    SYMi = getSymbols(ASETi, chainID)
    return (Vi, Ai, SYMi)


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


def getNFTInfos(chainID) -> List[DataNFT]:
    """
    @description
      Fetch, filter and return all NFTs on the chain

    @return
      nftInfo -- list of DataNFT objects
    """

    NFTinfo = _getNFTInfos(chainID)

    if chainID != networkutil.DEV_CHAINID:
        # filter if not on dev chain
        NFTinfo = _filterNftinfos(NFTinfo)

    return NFTinfo


def _getNFTInfos(chainID) -> List[DataNFT]:
    """
    @description
      Return all NFTs on the chain

    @return
      nftInfo -- list of DataNFT objects
    """
    NFTinfo = []
    chunk_size = 1000
    offset = 0

    while True:
        query = """
      {
         nfts(first: %d, skip: %d) {
            id
            symbol
        }
      }
      """ % (
            chunk_size,
            offset,
        )
        result = submitQuery(query, chainID)
        nfts = result["data"]["nfts"]
        if len(nfts) == 0:
            # means there are no records left
            break

        for nft in nfts:
            datanft = DataNFT(
                nft["id"],
                chainID,
                nft["symbol"],
            )
            NFTinfo.append(datanft)

        offset += chunk_size

    return NFTinfo


def getNFTVolumes(
    st_block: int, end_block: int, chainID: int
) -> Dict[str, Dict[str, float]]:
    """
    @description
      Query the chain for datanft volumes within the given block range.

    @return
      nft_vols_at_chain -- dict of [basetoken_addr][nft_addr]:vol_amt
    """
    print("getVolumes(): begin")

    NFTvols: Dict[str, Dict[str, float]] = {}

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
              dispensers {
                id
              }
            },
            lastPriceToken,
            lastPriceValue,
            block,
            gasPrice,
            gasUsed
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
            if len(order["datatoken"]["dispensers"]) == 0 and lastPriceValue == 0:
                continue
            basetoken_addr = order["lastPriceToken"]
            nft_addr = order["datatoken"]["nft"]["id"].lower()

            # Calculate gas cost
            gasCostWei = int(order["gasPrice"]) * int(order["gasUsed"])

            # deduct 1 wei so it's not profitable for free assets
            gasCost = fromBase18(gasCostWei - 1)
            native_token_addr = networkutil.CHAIN_ADDRS[chainID]

            # add gas cost value
            if gasCost > 0:
                if native_token_addr not in NFTvols:
                    NFTvols[native_token_addr] = {}

                if nft_addr not in NFTvols[native_token_addr]:
                    NFTvols[native_token_addr][nft_addr] = 0

                NFTvols[native_token_addr][nft_addr] += gasCost
            # ----

            if lastPriceValue == 0:
                continue

            # add lastPriceValue
            if basetoken_addr not in NFTvols:
                NFTvols[basetoken_addr] = {}

            if nft_addr not in NFTvols[basetoken_addr]:
                NFTvols[basetoken_addr][nft_addr] = 0.0
            NFTvols[basetoken_addr][nft_addr] += lastPriceValue

    print("getVolumes(): done")
    return NFTvols


@enforce_types
def _filterDids(nft_dids: List[str]) -> List[str]:
    """
    @description
      Filter out DIDs that are in purgatory and are not in Aquarius
    """
    nft_dids = _filterOutPurgatory(nft_dids)
    nft_dids = _filterToAquariusAssets(nft_dids)
    return nft_dids


@enforce_types
def _filterOutPurgatory(nft_dids: List[str]) -> List[str]:
    """
    @description
      Return dids that aren't in purgatory

    @arguments
      nft_dids: list of dids

    @return
      filtered_dids: list of filtered dids
    """
    bad_dids = _didsInPurgatory()
    filtered_dids = set(nft_dids) - set(bad_dids)
    return list(filtered_dids)


@enforce_types
def _filterNftinfos(nftinfos: List[DataNFT]) -> List[DataNFT]:
    """
    @description
      Filter out NFTs that are in purgatory and are not in Aquarius

    @arguments
      nftinfos: list of DataNFT objects

    @return
      filtered_nftinfos: list of filtered DataNFT objects
    """
    nft_dids = [nft.did for nft in nftinfos]
    nft_dids = _filterDids(nft_dids)
    filtered_nftinfos = [nft for nft in nftinfos if nft.did in nft_dids]
    return filtered_nftinfos


@enforce_types
def _filterNftvols(nftvols: dict, chainID: int) -> dict:
    """
    @description
      Filters out nfts that are in purgatory and are not in Aquarius

    @arguments
      nftvols: dict of [basetoken_addr][nft_addr]:vol_amt
      chainID: int

    @return
      filtered_nftvols: list of [basetoken_addr][nft_addr]:vol_amt
    """
    if chainID == networkutil.DEV_CHAINID:
        # can't filter on dev chain:
        return nftvols

    filtered_nftvols: Dict[str, Dict[str, float]] = {}
    nft_dids = []

    for basetoken_addr in nftvols:
        for nft_addr in nftvols[basetoken_addr]:
            nft_dids.append(oceanutil.calcDID(nft_addr, chainID))

    filtered_dids = _filterDids(nft_dids)

    for basetoken_addr in nftvols:
        for nft_addr in nftvols[basetoken_addr]:
            did = oceanutil.calcDID(nft_addr, chainID)
            if did in filtered_dids:
                if basetoken_addr not in filtered_nftvols:
                    filtered_nftvols[basetoken_addr] = {}
                filtered_nftvols[basetoken_addr][nft_addr] = nftvols[basetoken_addr][
                    nft_addr
                ]

    return filtered_nftvols


@enforce_types
def _filterToAquariusAssets(nft_dids: List[str]) -> List[str]:
    """
    @description
      Filter a list of nft_dids to only those that are in Aquarius

    @arguments
      nft_dids: list of nft_dids

    @return
      filtered_dids: list of filtered nft_dids
    """
    filtered_nft_dids = []

    assets = aquarius_asset_names(nft_dids)

    # Aquarius returns "" as the name for assets that isn't in the marketplace
    for did in assets:
        if assets[did] != "":
            filtered_nft_dids.append(did)

    return filtered_nft_dids


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

    approved_tokens.add(
        chainID,
        networkutil.CHAIN_ADDRS[chainID],
        networkutil._CHAINID_TO_NATIVE_TOKEN[chainID],
    )

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
def aquarius_asset_names(
    nft_dids: List[str],
) -> Dict[str, str]:
    """
    @description
      Return mapping of did -> asset name

    @params
      nft_dids -- array of dids

    @return
      did_to_asset_name -- dict of [did] : asset_name
    """

    # Remove duplicates
    nft_dids = list(set(nft_dids))

    # make a post request to Aquarius
    url = f"{AQUARIUS_BASE_URL}/api/aquarius/assets/names"

    headers = {"Content-Type": "application/json"}

    did_to_asset_name = {}

    BATCH_SIZE = 9042
    RETRY_ATTEMPTS = 3

    error_counter = 0
    # Send in chunks
    for i in range(0, len(nft_dids), BATCH_SIZE):
        # Aquarius expects "didList": ["did:op:...", ...]
        payload = json.dumps({"didList": nft_dids[i : i + BATCH_SIZE]})

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

    return did_to_asset_name
