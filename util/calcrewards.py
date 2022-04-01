#Draws from https://github.com/oceanprotocol/df-js/blob/main/script/index.js

import brownie
from enforce_typing import enforce_types
import json
import numpy
from numpy import log10
from pprint import pprint
import requests
from typing import Dict, List, Set

from util import oceanutil
from util.blockrange import BlockRange
from util.constants import BROWNIE_PROJECT as B
from util.oceanutil import calcDID
from util.graphutil import submitQuery

@enforce_types
def queryAndCalcRewards(rng:BlockRange, OCEAN_avail:float, 
                        subgraph_url:str) -> Dict[str, float]:
    """ @return -- rewards -- dict of [LP_addr] : OCEAN_float"""
    print("==calcRewards(): begin==")
    print(f"OCEAN available = {OCEAN_avail}")
    print(f"{rng}")

    #grab data from chain
    pools = getPools(subgraph_url)
    stakes = getStakes(pools, rng, subgraph_url) 
    pool_vols = getPoolVolumes(pools,rng.st,rng.fin,subgraph_url)

    #calc rewards
    rewards = calcRewards(stakes, pool_vols, OCEAN_avail)
    print("rewards: (OCEAN for each LP address)")
    pprint(rewards)

    print("==calcRewards(): done==")
    return rewards

@enforce_types
def getPools(subgraph_url:str) -> list: #list of BPool
    print("getPools(): begin")
    pools = getAllPools(subgraph_url)    
    pools = _filterToApprovedTokens(pools, subgraph_url)
    pools = _filterOutPurgatory(pools)
    print(f"  Got {len(pools)} pools")
    print("getPools(): done")
    return pools
   
@enforce_types
def calcRewards(stakes:dict, pool_vols:dict, OCEAN_avail:float):
    """
    @arguments
      stakes - dict of [pool_addr][LP_addr] : stake
      pool_vols -- dict of [pool_addr] -> vol
      OCEAN_avail -- float

    @return
      rewards -- dict of [LP_addr] : OCEAN_float
    """
    print("_calcRewardPerLP(): begin")

    #base data
    pool_addrs = list(pool_vols.keys())
    LP_addrs = list({addr for addrs in stakes.values() for addr in addrs})

    #fill in R
    rewards = {} # [LP_addr] : OCEAN_float
    for i, LP_addr in enumerate(LP_addrs):
        rewards[LP_addr] = 0.0
        for j, pool_addr in enumerate(pool_addrs):
            if pool_addr not in stakes: continue
            Sij = stakes[pool_addr].get(LP_addr, 0.0)
            Cj = pool_vols.get(pool_addr, 0.0)
            if Sij == 0 or Cj == 0: continue
            RF_ij = log10(Sij + 1.0) * log10(Cj + 2.0) #main formula!
            rewards[LP_addr] += RF_ij

    #normalize and scale rewards
    sum_ = sum(rewards.values())
    for LP_addr, reward in rewards.items():
        rewards[LP_addr] = reward / sum_ * OCEAN_avail

    #return dict
    print("_calcRewardPerLP(): done")
    return rewards

@enforce_types
def getStakes(pools:list, rng:BlockRange, subgraph_url:str):
    """@return - stakes - dict of [pool_addr][LP_addr] : stake"""
    print("getStakes(): begin")
    SSBOT_address = oceanutil.Staking().address.lower()
    stakes = {}
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
                  id
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
                pool_addr = d["pool"]["id"].lower()
                LP_addr = d["user"]["id"].lower()
                shares = float(d["shares"])
                if LP_addr == SSBOT_address: continue #skip ss bot
                if pool_addr not in stakes:
                    stakes[pool_addr] = {}
                if LP_addr not in stakes[pool_addr]:
                    stakes[pool_addr][LP_addr] = 0.0
                stakes[pool_addr][LP_addr] += shares / n_blocks
            offset += chunk_size

    return stakes
    print("getStakes(): done")
    return S

@enforce_types
def getPoolVolumes(pools:list, st_block:int, end_block:int, subgraph_url:str) \
    -> Dict[str, float]:
    """Return dict of [pool_addr] : vol"""

    DT_vols = getDTVolumes(st_block, end_block, subgraph_url) # [DT_addr] : vol

    pool_vols = {}
    for pool in pools:
        DT_addr = pool.getDatatokenAddress().lower()
        if DT_addr in DT_vols:
            pool_vols[pool.address.lower()] = DT_vols[DT_addr]
            
    return pool_vols

def getDTVolumes(st_block:int, end_block:int, subgraph_url:str) \
    -> Dict[str, float]: # [DT_addr] -> volume
    
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
def _filterToApprovedTokens(pools:list, subgraph_url:str) -> list:#list of BPool
    """Only keep pools that have approved basetokens (e.g. OCEAN)"""
    approved_tokens = getApprovedTokens(subgraph_url) #list of addr_str
    assert approved_tokens, "no approved tokens"
    return [pool for pool in pools
            if pool.getBaseTokenAddress() in approved_tokens]

@enforce_types
def getApprovedTokens(subgraph_url:str) -> List[str]: #list of BPool
    """Return addresses of approved basetokens"""
    query = "{ opcs{approvedTokens} }"
    result = submitQuery(query, subgraph_url)
    return result['data']['opcs'][0]['approvedTokens']

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
            id
            datatoken {
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
            pool = B.BPool.at(d["id"])
            pool.nft_addr = d["datatoken"]["nft"]["id"].lower()
            pools.append(pool)
        
    return pools
        

