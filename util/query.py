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
        is_purgatory: bool = False,
    ):
        self.nft_addr = nft_addr
        self.did = oceanutil.calcDID(nft_addr, chain_id)
        self.chain_id = chain_id
        self.symbol = _symbol
        self.name = ""
        self.is_purgatory = is_purgatory

    def setName(self, name: str):
        self.name = name

    def __repr__(self):
        return f"{self.nft_addr} {self.chain_id} {self.name} {self.symbol}"


@enforce_types
def queryNftvolsAndSymbols(
    rng: BlockRange, chainID: int
) -> Tuple[Dict[str, Dict[str, float]], Dict[str, str]]:
    """
    @description
      Return nftvols for the input block range and chain.

    @return
      nftvols_at_chain -- dict of [basetoken_addr][nft_addr] : vol
      symbols_at_chain -- dict of [basetoken_addr] : basetoken_symbol

    @notes
      A stake or nftvol value is in terms of basetoken (eg OCEAN, H2O).
      Basetoken symbols are full uppercase, addresses are full lowercase.
    """
    Vi_unfiltered = _queryNftvolumes(rng.st, rng.fin, chainID)
    Vi = _filterNftvols(Vi_unfiltered, chainID)

    # get all basetokens from Vi
    basetokens = TokSet()
    for basetoken in Vi:
        _symbol = symbol(basetoken)
        basetokens.add(chainID, basetoken, _symbol)
    SYMi = getSymbols(basetokens, chainID)
    return (Vi, SYMi)


@enforce_types
def queryVebalances(
    rng: BlockRange, CHAINID: int
) -> Tuple[Dict[str, float], Dict[str, float], Dict[str, int]]:
    """
    @description
      Return all ve balances

    @return
      vebals -- dict of [LP_addr] : veOCEAN_float
      locked_amt -- dict of [LP_addr] : locked_amt
      unlock_time -- dict of [LP_addr] : unlock_time
    """
    MAX_TIME = 4 * 365 * 86400  # max lock time

    # [LP_addr] : veBalance
    vebals: Dict[str, float] = {}

    # [LP_addr] : locked_amt
    locked_amt: Dict[str, float] = {}

    # [LP_addr] : lock_time
    unlock_time: Dict[str, int] = {}

    unixEpochTime = brownie.network.chain.time()
    n_blocks = rng.numBlocks()
    n_blocks_sampled = 0
    blocks = rng.getBlocks()
    print("queryVebalances: begin")

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
                if user["id"] not in vebals:
                    vebals[user["id"]] = balance
                else:
                    vebals[user["id"]] += balance

                ## set locked amount
                # always get the latest
                locked_amt[user["id"]] = float(user["lockedAmount"])

                ## set unlock time
                # always get the latest
                unlock_time[user["id"]] = int(user["unlockTime"])

            ## increase offset
            offset += chunk_size
        n_blocks_sampled += 1

    assert n_blocks_sampled > 0

    # get average
    for user in vebals:
        vebals[user] /= n_blocks_sampled

    print("queryVebalances: done")

    return vebals, locked_amt, unlock_time


@enforce_types
def queryAllocations(
    rng: BlockRange, CHAINID: int
) -> Dict[int, Dict[str, Dict[str, float]]]:
    """
    @description
      Return all allocations.

    @return
      allocations -- dict of [chain_id][nft_addr][LP_addr]: percent
    """

    # [chain_id][nft_addr][LP_addr] : percent
    allocs: Dict[int, Dict[str, Dict[str, float]]] = {}

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
            _allocs = result["data"]["veAllocateUsers"]
            if len(_allocs) == 0:
                # means there are no records left
                break

            for allocation in _allocs:
                LP_addr = allocation["id"]
                for ve_allocation in allocation["veAllocation"]:
                    nft_addr = ve_allocation["nftAddress"]
                    chain_id = ve_allocation["chainId"]
                    allocated = float(ve_allocation["allocated"])

                    if chain_id not in allocs:
                        allocs[chain_id] = {}
                    if nft_addr not in allocs[chain_id]:
                        allocs[chain_id][nft_addr] = {}

                    if LP_addr not in allocs[chain_id][nft_addr]:
                        allocs[chain_id][nft_addr][LP_addr] = allocated
                    else:
                        allocs[chain_id][nft_addr][LP_addr] += allocated

            offset += chunk_size
        n_blocks_sampled += 1

    assert n_blocks_sampled > 0

    # get average
    for chain_id in allocs:
        for nft_addr in allocs[chain_id]:
            for LP_addr in allocs[chain_id][nft_addr]:
                allocs[chain_id][nft_addr][LP_addr] /= n_blocks_sampled

    # get total allocs per each LP
    lp_total = {}
    for chain_id in allocs:
        for nft_addr in allocs[chain_id]:
            for LP_addr in allocs[chain_id][nft_addr]:
                if LP_addr not in lp_total:
                    lp_total[LP_addr] = 0.0
                lp_total[LP_addr] += allocs[chain_id][nft_addr][LP_addr]

    for LP_addr in lp_total:
        if lp_total[LP_addr] < MAX_ALLOCATE:
            lp_total[LP_addr] = MAX_ALLOCATE

    # normalize values per LP
    for chain_id in allocs:
        for nft_addr in allocs[chain_id]:
            for LP_addr in allocs[chain_id][nft_addr]:
                if lp_total[LP_addr] == 0.0:
                    print(f"WARNING: {lp_total[LP_addr]} == 0.0")
                    continue
                allocs[chain_id][nft_addr][LP_addr] /= lp_total[LP_addr]

    return allocs


def queryNftinfo(chainID) -> List[DataNFT]:
    """
    @description
      Fetch, filter and return all NFTs on the chain

    @return
      nftInfo -- list of DataNFT objects
    """

    nftinfo = _queryNftinfo(chainID)

    if chainID != networkutil.DEV_CHAINID:
        # filter if not on dev chain
        nftinfo = _filterNftinfos(nftinfo)
        nftinfo = _markPurgatoryNfts(nftinfo)
        nftinfo = _populateNftAssetNames(nftinfo)

    return nftinfo


def _populateNftAssetNames(nftInfo: List[DataNFT]) -> List[DataNFT]:
    """
    @description
      Populate the list of NFTs with the asset names

    @return
      nftInfo -- list of DataNFT objects
    """

    nft_dids = [nft.did for nft in nftInfo]
    did_to_name = queryAquariusAssetNames(nft_dids)

    for nft in nftInfo:
        nft.setName(did_to_name[nft.did])

    return nftInfo


def _queryNftinfo(chainID) -> List[DataNFT]:
    """
    @description
      Return all NFTs on the chain

    @return
      nftInfo -- list of DataNFT objects
    """
    nftinfo = []
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
            nftinfo.append(datanft)

        offset += chunk_size

    return nftinfo


def _queryNftvolumes(
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
            lastPriceToken{
              id
            },
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
        if "errors" in result:
            raise AssertionError(result)
        new_orders = result["data"]["orders"]

        if new_orders == []:
            break
        for order in new_orders:
            lastPriceValue = float(order["lastPriceValue"])
            if len(order["datatoken"]["dispensers"]) == 0 and lastPriceValue == 0:
                continue
            basetoken_addr = order["lastPriceToken"]["id"]
            nft_addr = order["datatoken"]["nft"]["id"].lower()

            # Calculate gas cost
            gasCostWei = int(order["gasPrice"]) * int(order["gasUsed"])

            # deduct 1 wei so it's not profitable for free assets
            gasCost = fromBase18(gasCostWei - 1)
            native_token_addr = networkutil._CHAINID_TO_ADDRS[chainID]

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
    nft_dids = _filterToAquariusAssets(nft_dids)
    filtered_nftinfos = [nft for nft in nftinfos if nft.did in nft_dids]
    return filtered_nftinfos


@enforce_types
def _markPurgatoryNfts(nftinfos: List[DataNFT]) -> List[DataNFT]:
    bad_dids = _didsInPurgatory()
    for nft in nftinfos:
        if nft.did in bad_dids:
            nft.is_purgatory = True
    return nftinfos


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

    assets = queryAquariusAssetNames(nft_dids)

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
def getSymbols(tokens: TokSet, chainID: int) -> Dict[str, str]:
    """
    @description
      Return mapping of basetoken addr -> symbol for this chain

    @return
      symbols_at_chain -- dict of [basetoken_addr] : basetoken_symbol
    """
    return {tok.address: tok.symbol for tok in tokens.toks if tok.chainID == chainID}


_ADDR_TO_SYMBOL = networkutil._ADDRS_TO_SYMBOL  # address : TOKEN_symbol


def symbol(addr: str):
    """Returns token symbol, given its address."""
    global _ADDR_TO_SYMBOL
    if addr not in _ADDR_TO_SYMBOL:
        _symbol = B.Simpletoken.at(addr).symbol()
        _symbol = _symbol.upper()  # follow lower-upper rules
        _ADDR_TO_SYMBOL[addr] = _symbol
    return _ADDR_TO_SYMBOL[addr]


@enforce_types
def queryAquariusAssetNames(
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
