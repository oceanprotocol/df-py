import json
from typing import Dict, List, Tuple

import requests
from enforce_typing import enforce_types

from util import oceanutil
from util.blockrange import BlockRange
from util.constants import BROWNIE_PROJECT as B
from util.graphutil import submitQuery
from util.tok import TokSet


@enforce_types
class SimplePool:
    """
    A simple object to store pools retrieved from chain.
    Easier to retrieve info than using dicts keyed by strings, and
      more lightweight than a full BPool object.
    """

    def __init__(
        self,
        addr: str,
        nft_addr: str,
        DT_addr: str,
        DT_symbol: str,
        basetoken_addr: str,
    ):
        self.addr = addr
        self.nft_addr = nft_addr
        self.DT_addr = DT_addr
        self.DT_symbol = DT_symbol
        self.basetoken_addr = basetoken_addr

    @property
    def basetoken_symbol(self) -> str:
        return symbol(self.basetoken_addr)

    def __str__(self):
        s = ["SimplePool={"]
        s += [f"addr={self.addr[:5]}"]
        s += [f", nft_addr={self.nft_addr[:5]}"]
        s += [f", DT_addr={self.DT_addr[:5]}"]
        s += [f", DT_symbol={self.DT_symbol}"]
        s += [f", basetoken_addr={self.basetoken_addr[:5]}"]
        s += [f", basetoken_symbol={self.basetoken_symbol}"]
        s += [" /SimplePool}"]
        return "".join(s)


@enforce_types
def query_all(rng: BlockRange, chainID: int) -> Tuple[list, dict, dict, TokSet]:
    """
    @description
      Return pool info, stakes & poolvols, for the input block range and chain.

    @return
      pools_at_chain -- list of SimplePool
      stakes_at_chain -- dict of [basetoken_addr][pool_addr][LP_addr] : stake
      poolvols_at_chain -- dict of [basetoken_addr][pool_addr] : vol
      approved_tokens -- TokSet

    @notes
      A stake or poolvol value is in terms of basetoken (eg OCEAN, H2O).
      Basetoken symbols are full uppercase, addresses are full lowercase.
    """
    Pi = getPools(chainID)
    Si = getStakes(Pi, rng, chainID)
    Vi = getPoolVolumes(Pi, rng.st, rng.fin, chainID)
    Ai = getApprovedTokens(chainID)
    return (Pi, Si, Vi, Ai)


@enforce_types
def getPools(chainID: int) -> list:
    """
    @description
      Return all pools eligible for DF.

    @return
      pools -- list of SimplePool
    """
    pools = getAllPools(chainID)
    pools = _filterOutPurgatory(pools, chainID)
    return pools


@enforce_types
def getStakes(pools: list, rng: BlockRange, chainID: int) -> dict:
    """
    @description
      Query the chain for stakes.

    @return
      stakes_at_chain -- dict of [basetoken_addr][pool_addr][LP_addr]:stake
    """
    print("getStakes(): begin")
    _ = pools  # little trick because pools isn't used
    SSBOT_address = oceanutil.Staking().address.lower()
    stakes: Dict[str, Dict[str, Dict[str, float]]] = {}
    n_blocks = rng.numBlocks()
    n_blocks_sampled = 0
    blocks = rng.getBlocks()
    for block_i, block in enumerate(blocks):  # loop across block groups
        if (block_i % 50) == 0 or (block_i == n_blocks - 1):
            print(f"  {(block_i+1) / float(n_blocks) * 100.0:.1f}% done")
        LP_offset = 0
        chunk_size = 1000  # max for subgraph=1000

        while True:  # loop across LP groups
            query = """
            { 
              poolShares(skip:%s, first:%s, block:{number:%s}) {
                pool {
                  id,
                  baseToken {
                    id
                  },
                }, 
                user {
                  id
                },
                shares
              }
            }
            """ % (
                LP_offset,
                chunk_size,
                block,
            )
            result = submitQuery(query, chainID)

            if (
                "errors" in result
                and "indexed up to block number" in result["errors"][0]["message"]
            ):
                LP_offset += chunk_size
                break

            new_pool_stake = result["data"]["poolShares"]

            if not new_pool_stake:
                break

            for d in new_pool_stake:
                basetoken_addr = d["pool"]["baseToken"]["id"].lower()
                pool_addr = d["pool"]["id"].lower()
                LP_addr = d["user"]["id"].lower()
                shares = float(d["shares"])
                if LP_addr == SSBOT_address:
                    continue  # skip ss bot

                if basetoken_addr not in stakes:
                    stakes[basetoken_addr] = {}
                if pool_addr not in stakes[basetoken_addr]:
                    stakes[basetoken_addr][pool_addr] = {}
                if LP_addr not in stakes[basetoken_addr][pool_addr]:
                    stakes[basetoken_addr][pool_addr][LP_addr] = 0.0

                stakes[basetoken_addr][pool_addr][LP_addr] += shares

            LP_offset += chunk_size
        n_blocks_sampled += 1
    # normalize stake based on # blocks sampled
    # (this may be lower than target # blocks, if we hit indexing errors)
    assert n_blocks_sampled > 0
    for basetoken_addr in stakes:  # pylint: disable=consider-iterating-dictionary
        for pool_addr in stakes[basetoken_addr]:
            for LP_addr in stakes[basetoken_addr][pool_addr]:
                stakes[basetoken_addr][pool_addr][LP_addr] /= n_blocks_sampled
    return stakes  # ie stakes_at_chain


@enforce_types
def getPoolVolumes(pools: list, st_block: int, end_block: int, chainID: int) -> dict:
    """
    @description
      Query the chain for pool volumes within the given block range.

    @return
      poolvols_at_chain -- dict of [basetoken_addr][pool_addr]:vol_amt
    """
    # [baseaddr][DT_addr]:vol
    DTvols_at_chain = getDTVolumes(st_block, end_block, chainID)

    # [baseaddr][pool_addr]:vol
    poolvols_at_chain: Dict[str, Dict[str, float]] = {}
    for baseaddr in DTvols_at_chain:  # pylint: disable=consider-iterating-dictionary
        if baseaddr not in poolvols_at_chain:
            poolvols_at_chain[baseaddr] = {}

        for DT_addr in DTvols_at_chain[baseaddr]:
            # handle if >1 pool has the DT
            pools_with_DT = [p for p in pools if p.DT_addr == DT_addr]
            vol = DTvols_at_chain[baseaddr][DT_addr]
            for pool in pools_with_DT:
                # the "/" spreads vol evenly among pools holding the DT
                poolvols_at_chain[baseaddr][pool.addr] = vol / len(pools_with_DT)

    return poolvols_at_chain


def getDTVolumes(
    st_block: int, end_block: int, chainID: int
) -> Dict[str, Dict[str, float]]:
    """
    @description
      Query the chain for datatoken (DT) volumes within the given block range.

    @return
      DTvols_at_chain -- dict of [basetoken_addr][DT_addr]:vol_amt
    """
    print("getDTVolumes(): begin")

    DTvols: Dict[str, Dict[str, float]] = {}
    chunk_size = 1000  # max for subgraph = 1000
    offset = 0
    while True:
        query = """
        {
          orders(where: {block_gte:%s, block_lte:%s}, skip:%s, first:%s) {
            id,
            datatoken {
              id
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
            DT_addr = order["datatoken"]["id"].lower()
            basetoken_addr = order["lastPriceToken"]

            if basetoken_addr not in DTvols:
                DTvols[basetoken_addr] = {}

            if DT_addr not in DTvols[basetoken_addr]:
                DTvols[basetoken_addr][DT_addr] = 0.0
            DTvols[basetoken_addr][DT_addr] += lastPriceValue

    print("getDTVolumes(): done")
    return DTvols  # ie DTvols_at_chain


@enforce_types
def _filterOutPurgatory(pools: List[SimplePool], chainID: int) -> List[SimplePool]:
    """
    @description
      Return pools that aren't in purgatory

    @arguments
      pools -- list of SimplePool

    @return
      filtered_pools -- list of SimplePool
    """
    bad_dids = _didsInPurgatory()
    filtered_pools = [
        pool
        for pool in pools
        if oceanutil.calcDID(pool.nft_addr, chainID) not in bad_dids
    ]
    return filtered_pools


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
def getAllPools(chainID: int) -> List[SimplePool]:
    """
    @description
      Query the chain and return all pools

    @return
      pools - list of SimplePool
    """
    pools = []
    offset = 0
    chunk_size = 1000  # max for subgraph = 1000

    while True:
        query = """
        {
          pools(skip:%s, first:%s){
            transactionCount,
            id,
            baseToken {
              id
            },
            datatoken {
                id,
                symbol,
                nft {
                    id
                }
            }
          }
        }
        """ % (
            offset,
            chunk_size,
        )
        offset += chunk_size
        result = submitQuery(query, chainID)
        ds = result["data"]["pools"]
        if ds == []:
            break  # if there are no pools left, break
        for d in ds:
            ## tx_count = int(d["transactionCount"])
            ## if tx_count == 0:
            ##     continue
            pool = SimplePool(
                addr=d["id"].lower(),
                nft_addr=d["datatoken"]["nft"]["id"].lower(),
                DT_addr=d["datatoken"]["id"].lower(),
                DT_symbol=d["datatoken"]["symbol"].upper(),
                basetoken_addr=d["baseToken"]["id"].lower(),
            )
            pools.append(pool)

    return pools


_ADDR_TO_SYMBOL = {}  # address : TOKEN_symbol


def symbol(addr: str):
    """Returns token symbol, given its address."""
    global _ADDR_TO_SYMBOL
    if addr not in _ADDR_TO_SYMBOL:
        _symbol = B.Simpletoken.at(addr).symbol()
        _symbol = _symbol.upper()  # follow lower-upper rules
        _ADDR_TO_SYMBOL[addr] = _symbol
    return _ADDR_TO_SYMBOL[addr]
