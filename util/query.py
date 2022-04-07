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

@enforce_types
def query(rng:BlockRange, subgraph_url:str) -> Tuple[dict, dict]:
    """
    @return
      stakes -- dict of [basetoken_symbol][pool_addr][LP_addr] : stake
      pool_vols -- dict of [basetoken_symbol][pool_addr] : vol
      
    A stake or vol value is in terms of basetoken (eg OCEAN, H2O).
    """
    pools = getPools(subgraph_url)
    stakes = getStakes(pools, rng, subgraph_url) 
    pool_vols = getPoolVolumes(pools,rng.st,rng.fin,subgraph_url)
    return (stakes, pool_vols)

@enforce_types
def getPools(subgraph_url:str) -> list: #list of BPool
    pools = getAllPools(subgraph_url)
    pools = _filterOutPurgatory(pools)
    return pools

@enforce_types
def getStakes(pools:list, rng:BlockRange, subgraph_url:str) -> dict:
    """@return - dict of [basetoken_symbol][pool_addr][LP_addr] : stake"""
    print("getStakes(): begin")
    SSBOT_address = oceanutil.Staking().address.lower()
    approved_tokens = getApprovedTokens(subgraph_url) # addr : symbol
    approved_token_addrs = set(d.keys())
    stakes = {symbol:{} for symbol in approved_tokens.values()}
    n_blocks = rng.numBlocks()
    blocks = rng.getBlocks()
    for block_i, block in enumerate(blocks):
        if (block_i % 50) == 0 or (block_i == n_blocks-1):
            print(f"  {(block_i+1) / float(n_blocks) * 100.0:.1f}% done")
        offset = 0
        chunk_size = 1000 #max for subgraph=1000
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
            """ % (offset, chunk_size, block)
            result = submitQuery(query, subgraph_url)
            new_pool_stake = result["data"]["poolShares"]
            if not new_pool_stake:
                break
            for d in new_pool_stake:
                base_token_addr = d["pool"]["basetoken"]["id"].lower()
                base_token_symbol = approved_tokens[base_token_addr]
                pool_addr = d["pool"]["id"].lower()
                LP_addr = d["user"]["id"].lower()
                shares = float(d["shares"])
                if base_token_addr not in approved_token_addrs: continue
                if LP_addr == SSBOT_address: continue #skip ss bot
                
                if base_token_symbol not in stakes:
                    stakes[base_token_symbol] = {}
                if pool_addr not in stakes[base_token_symbol]:
                    stakes[base_token_symbol][pool_addr] = {}
                if LP_addr not in stakes[base_token_symbol][pool_addr]:
                    stakes[base_token_symbol][pool_addr][LP_addr] = 0.0
                    
                stakes[base_token_symbol][pool_addr][LP_addr] += shares / n_blocks
            offset += chunk_size

    return stakes

@enforce_types
def getPoolVolumes(pools:list, st_block:int, end_block:int, subgraph_url:str) \
    -> dict:
    """@return - dict of [basetoken_symbol][pool_addr] : vol"""
    DT_vols = getDTVolumes(st_block, end_block, subgraph_url) # DT_addr : vol
    DTs_with_consume = set(DT_vols.keys())
    approved_tokens = getApprovedTokens(subgraph_url) # basetoken_addr : symbol

    # dict of [basetoken_symbol][pool_addr] : vol
    pool_vols = {symbol:{} for symbol in approved_tokens.values()}
    for pool in pools:
        if pool.DT_addr in DTs_with_consume: 
            basetoken_symbol = approved_tokens[pool.basetoken_addr]
            pool_vols[basetoken_symbol][pool.addr] = DT_vols[pool.DT_addr]
            
    return pool_vols

def getDTVolumes(st_block:int, end_block:int, subgraph_url:str) \
    -> Dict[str, float]:
    """Return dict of [DT_addr] -> vol"""
    print("getDTVolumes(): begin")
    OCEAN_addr = oceanutil.OCEANtoken().address.lower()
    
    DT_vols = {}
    chunk_size = 1000 #max for subgraph = 1000
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
        """ % (st_block, end_block, offset, chunk_size)
        result = submitQuery(query, subgraph_url)
        new_orders = result["data"]["orders"]
        for order in new_orders:
            if (order["lastPriceToken"].lower() == OCEAN_addr):
                DT_addr = order["datatoken"]["id"].lower()
                lastPriceValue = float(order["lastPriceValue"])
                if DT_addr not in DT_vols:
                    DT_vols[DT_addr] = 0.0
                DT_vols[DT_addr] += lastPriceValue
                
    print("getDTVolumes(): done")
    return DT_vols

@enforce_types
def _filterOutPurgatory(pools:list) -> list: #list of BPool
    """return pools that aren't in purgatory"""
    bad_dids = _didsInPurgatory()
    return [pool for pool in pools
            if calcDID(pool.nft_addr) not in bad_dids]

@enforce_types
def _didsInPurgatory() -> List[str]:
    """return dids that are in purgatory"""
    url = "https://raw.githubusercontent.com/oceanprotocol/list-purgatory/main/list-assets.json"
    resp = requests.get(url)

    #list of {'did' : 'did:op:6F7...', 'reason':'..'}
    data = json.loads(resp.text)

    return [item['did'] for item in data]
    
@enforce_types
def getApprovedTokens(subgraph_url:str) -> Dict[str,str]:
    """@return - dict of [token_addr] : token_symbol"""
    query = "{ opcs{approvedTokens} }"
    result = submitQuery(query, subgraph_url)
    addrs = result['data']['opcs'][0]['approvedTokens']
    d = {addr.lower() : B.Simpletoken.at(addr).symbol() for addr in addrs}
    assert len(addrs) == len(set(d.values())), "symbols not unique, eek"
    return d

@enforce_types
def getAllPools(subgraph_url:str) -> list: #list of BPool
    pools = []
    offset = 0
    chunk_size = 1000 #max for subgraph = 1000
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
        """ % (offset, chunk_size)
        result = submitQuery(query, subgraph_url)
        ds = result['data']['pools']
        for d in ds:
            tx_count = int(d["transactionCount"])
            if tx_count == 0: continue
            pool = SimplePool(
                addr=d["id"].lower(),
                nft_addr=d["datatoken"]["nft"]["id"].lower(),
                DT_addr=d["datatoken"]["id"].lower(),
                basetoken_addr=d["baseToken"]["id"].lower())
            pools.append(pool)
        
    return pools

class SimplePool:
    def __init__(self, addr:str, nft_addr:str,
                 DT_addr:str, basetoken_addr:str):
        self.addr = addr
        self.nft_addr = nft_addr
        self.DT_addr = DT_addr
        self.basetoken_addr = basetoken_addr

