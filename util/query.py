import brownie
from enforce_typing import enforce_types
import json
import numpy
from numpy import log10
from pprint import pprint
import requests
from typing import Dict, List, Set, Tuple

from util import oceanutil
from util.blockrange import BlockRange
from util.constants import BROWNIE_PROJECT as B
from util.oceanutil import calcDID
from util.graphutil import submitQuery


class SimplePool:
    """
    A simple object to store pools retrieved from chain.
    Easier to retrieve info than using dicts keyed by strings, and
      more lightweight than a full BPool object.
    """
    def __init__(self, addr: str, nft_addr: str, DT_addr: str, basetoken_addr: str):
        self.addr = addr
        self.nft_addr = nft_addr
        self.DT_addr = DT_addr
        self.basetoken_addr = basetoken_addr


@enforce_types
def query(rng: BlockRange, subgraph_url: str) -> Tuple[dict, dict]:
    """
    @description
      Return stakes and poolvols at the chain of the subgraph_url

    @return
      stakes_at_chain -- dict of [basetoken_symbol][pool_addr][LP_addr] : stake
      poolvols_at_chain -- dict of [basetoken_symbol][pool_addr] : vol

    @notes
      A stake or poolvol value is in terms of basetoken (eg OCEAN, H2O).
    """
    pools = getPools(subgraph_url)
    Si = getStakes(pools, rng, subgraph_url)
    Vi = getPoolVolumes(pools, rng.st, rng.fin, subgraph_url)
    return (Si, Vi) #i.e. (stakes_at_chain, poolvols_at_chain)


@enforce_types
def getPools(subgraph_url: str) -> list:  # list of BPool
    pools = getAllPools(subgraph_url)
    pools = _filterOutPurgatory(pools)
    return pools


@enforce_types
def getStakes(pools: list, rng: BlockRange, subgraph_url: str) -> dict:
    """
    @description
      Return stakes at the chain of the subgraph_url

    @return
      stakes_at_chain -- dict of [basetoken_symbol][pool_addr][LP_addr]:stake
    """
    print("getStakes(): begin")
    SSBOT_address = oceanutil.Staking().address.lower()
    approved_tokens = getApprovedTokens(subgraph_url)  # addr : symbol
    approved_token_addrs = set(approved_tokens.keys())
    stakes = {symbol: {} for symbol in approved_tokens.values()}
    n_blocks = rng.numBlocks()
    blocks = rng.getBlocks()
    for block_i, block in enumerate(blocks):
        if (block_i % 50) == 0 or (block_i == n_blocks - 1):
            print(f"  {(block_i+1) / float(n_blocks) * 100.0:.1f}% done")
        offset = 0
        chunk_size = 1000  # max for subgraph=1000
        while True:
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
                offset,
                chunk_size,
                block,
            )
            result = submitQuery(query, subgraph_url)
            new_pool_stake = result["data"]["poolShares"]
            if not new_pool_stake:
                break
            for d in new_pool_stake:
                base_token_addr = d["pool"]["baseToken"]["id"].lower()
                base_token_symbol = approved_tokens[base_token_addr].lower()
                pool_addr = d["pool"]["id"].lower()
                LP_addr = d["user"]["id"].lower()
                shares = float(d["shares"])
                if base_token_addr not in approved_token_addrs:
                    continue
                if LP_addr == SSBOT_address:
                    continue  # skip ss bot

                if base_token_symbol not in stakes:
                    stakes[base_token_symbol] = {}
                if pool_addr not in stakes[base_token_symbol]:
                    stakes[base_token_symbol][pool_addr] = {}
                if LP_addr not in stakes[base_token_symbol][pool_addr]:
                    stakes[base_token_symbol][pool_addr][LP_addr] = 0.0

                stakes[base_token_symbol][pool_addr][LP_addr] += shares / n_blocks
            offset += chunk_size

    return stakes #ie stakes_at_chain


@enforce_types
def getPoolVolumes(
    pools: list, st_block: int, end_block: int, subgraph_url: str) \
    -> dict:
    """
    @description
      Return poolvols at the chain of the subgraph_url

    @return
      poolvols_at_chain -- dict of [basetoken_symbol][pool_addr]:vol_amt
    """
    DT_vols = getDTVolumes(st_block, end_block, subgraph_url)  # DT_addr : vol
    DTs_with_consume = set(DT_vols.keys())
    approved_tokens = getApprovedTokens(subgraph_url)  # basetoken_addr : symbol

    # dict of [basetoken_symbol][pool_addr] : vol
    poolvols = {symbol: {} for symbol in approved_tokens.values()}
    for pool in pools:
        if pool.DT_addr in DTs_with_consume:
            basetoken_symbol = approved_tokens[pool.basetoken_addr]
            poolvols[basetoken_symbol][pool.addr] = DT_vols[pool.DT_addr]

    return poolvols #ie poolvols_at_chain


def getDTVolumes(st_block: int, end_block: int, subgraph_url: str) \
    -> Dict[str, float]:
    """
    @description
      Return estimated datatoken (DT) volumes within given start:end block
      range, at the chain of the subgraph_url

    @return
      DTvols_at_chain -- dict of [DT_addr]:vol_amt
    """
    print("getDTVolumes(): begin")
    OCEAN_addr = oceanutil.OCEANtoken().address.lower()

    DT_vols = {}
    chunk_size = 1000  # max for subgraph = 1000
    for offset in range(0, end_block - st_block, chunk_size):
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
        result = submitQuery(query, subgraph_url)
        new_orders = result["data"]["orders"]
        for order in new_orders:
            if order["lastPriceToken"].lower() == OCEAN_addr:
                DT_addr = order["datatoken"]["id"].lower()
                lastPriceValue = float(order["lastPriceValue"])
                if DT_addr not in DT_vols:
                    DT_vols[DT_addr] = 0.0
                DT_vols[DT_addr] += lastPriceValue

    print("getDTVolumes(): done")
    return DT_vols #ie DTvols_at_chain


@enforce_types
def _filterOutPurgatory(pools: List[SimplePool]) -> List[SimplePool]:
    """
    @description
      Return pools that aren't in purgatory

    @arguments
      pools -- list of SimplePool

    @return
      filtered_pools -- list of SimplePool
    """
    bad_dids = _didsInPurgatory()
    filtered_pools = [pool
                      for pool in pools
                      if calcDID(pool.nft_addr) not in bad_dids]
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
def getApprovedTokens(subgraph_url: str) -> Dict[str, str]:
    """
    @description
      Return basetokens that are 'approved', ie eligible for data farming
    
    @return
      d - dict of [token_addr] : token_symbol
    """
    query = "{ opcs{approvedTokens} }"
    result = submitQuery(query, subgraph_url)
    addrs = result["data"]["opcs"][0]["approvedTokens"]
    d = {addr.lower(): B.Simpletoken.at(addr).symbol().lower()
         for addr in addrs}
    assert len(addrs) == len(set(d.values())), "symbols not unique, eek"
    return d


@enforce_types
def getAllPools(subgraph_url: str) -> List[SimplePool]:
    """
    @description
      Query the chain and return all pools
    
    @return
      pools - list of SimplePool
    """
    pools = []
    offset = 0
    chunk_size = 1000  # max for subgraph = 1000
    num_blocks = len(brownie.network.chain)
    for offset in range(0, num_blocks, chunk_size):
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
        result = submitQuery(query, subgraph_url)
        ds = result["data"]["pools"]
        for d in ds:
            tx_count = int(d["transactionCount"])
            if tx_count == 0:
                continue
            pool = SimplePool(
                addr=d["id"].lower(),
                nft_addr=d["datatoken"]["nft"]["id"].lower(),
                DT_addr=d["datatoken"]["id"].lower(),
                basetoken_addr=d["baseToken"]["id"].lower(),
            )
            pools.append(pool)

    return pools

