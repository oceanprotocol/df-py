#Draws from https://github.com/oceanprotocol/df-js/blob/main/script/index.js

import brownie
from enforce_typing import enforce_types
import json
import numpy
from numpy import log10
from pprint import pprint
import requests
from typing import Dict, List

from util import oceanutil
from util.blockrange import BlockRange
from util.constants import BROWNIE_PROJECT as B
from util.oceanutil import calcDID
from util.graphutil import submitQuery

@enforce_types
def calcRewards(OCEAN_available:float, block_range:BlockRange,
                subgraph_url:str) -> Dict[str, float]:
    """ @return -- rewards -- dict of [LP_addr] : OCEAN_float"""
    print("==calcRewards(): begin==")
    print(f"OCEAN_available: {OCEAN_available}")
    print(f"block_range: {block_range}")

    #[LP_i] : LP_addr
    LPs:List[str] = getLPs(block_range, subgraph_url) 

    #[pool_j] : BPool
    pools:list = getPools(subgraph_url)

    #DT_addr : OCEAN_vol
    DT_vols = getConsumeVolumes(
        block_range.start_block, block_range.end_block, subgraph_url)

    #[pool_j] : OCEAN_vol
    pool_vols = []
    for pool in pools:
        DT_addr = pool.getDatatokenAddress()
        vol = DT_vols.get(DT_addr, 0.0)
        pool_vols.append(vol)

    #[LP_i,pool_j] : stake
    S = getStake(LPs, pools, block_range, subgraph_url) 

    #[LP_i] : OCEAN_reward
    R = _calcRewardPerLP(pool_vols, S, OCEAN_available)

    #[LP_addr] : OCEAN_reward
    rewards = {addr:R[i] for i,addr in enumerate(LPs)}
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
def getLPs(block_range:BlockRange, subgraph_url:str) -> List[str]:
    """@return -- list of [LP_i] : LP_addr"""
    SSBOT_address = oceanutil.Staking().address.lower()
    LP_set = set()

    print("getLPs(): begin")
    n_blocks = block_range.numBlocks()
    for block_i, block in enumerate(block_range.getRange()):
        if (block_i % 50) == 0 or (block_i == n_blocks-1):
            print(f"  {(block_i+1) / float(n_blocks) * 100.0:.1f}% done")

        chunk_size = 1000 #max for subgraph = 1000
        offset = 0
        while True:
            query = """
            {
              poolShares(skip:%s, first:%s, block:{number:%s}) {
                pool {
                  id,
                  totalShares
                }
                shares,
                user {
                  id
                }
              }
            }
            """ % (offset, chunk_size, block)
            result = submitQuery(query, subgraph_url)
            new_pool_stake = result["data"]["poolShares"]
            if not new_pool_stake:
                break
            for d in new_pool_stake:
                LP_addr = d["user"]["id"]
                if LP_addr.lower()  == SSBOT_address: continue #skip ss bot
                
                shares = float(d["shares"])
                if shares == 0.0: continue
                LP_set.add(LP_addr)       
            offset += chunk_size

    print(f"  Got {len(LP_set)} LPs")
    print("getLPs(): done")
    return list(LP_set)
   
@enforce_types
def _calcRewardPerLP(C:List[float], S, OCEAN_available:float):
    """
    @arguments
      pool_vols -- list of [pool_j] : consume_volume_in_OCEAN_float
      S -- 2d array of [LP_i,pool_j] : share_float
      OCEAN_available -- float

    @return
      R -- rewards -- 1d array of [LP_i] : OCEAN_float
    """
    print("_calcRewardPerLP(): begin")
    (num_LPs, num_pools) = S.shape
    R = numpy.zeros((num_LPs,), dtype=float)

    for i in range(num_LPs):
        for j in range(num_pools):
            if S[i,j] == 0.0:
                continue
            RF_ij = log10(S[i,j] + 1.0) * log10(C[j] + 2.0)
            R[i] += RF_ij

    #normalize, and scale
    R = R / sum(R) * OCEAN_available

    print("_calcRewardPerLP(): done")
    return R

@enforce_types
def getStake(LPs:List[str], pools:list,
             block_range:BlockRange, subgraph_url:str):
    """
    @arguments
      LPs -- list of [LP_i] : LP_addr
      pools -- list of [pool_j] : BPool
      block_range -- BlockRange
      subgraph_url -- str

    @return
      S -- 2d array [LP_i, pool_j] : relative_stake_float -- stake in pool
    """
    print("getStake(): begin")
    SSBOT_address = oceanutil.Staking().address.lower()

    #[LP_addr] : LP_i
    LP_dict = {addr:i for i,addr in enumerate(LPs)}

    #[pool_addr] : pool_j
    pool_dict = {pool.address:j for j,pool in enumerate(pools)} 
    
    num_LPs, num_pools = len(LPs), len(pools)
    S = numpy.zeros((num_LPs, num_pools), dtype=float)

    n_blocks = block_range.numBlocks()
    blocks = block_range.getRange()
    for block_i, block in enumerate(blocks):
        if (block_i % 50) == 0 or (block_i == n_blocks-1):
            print(f"  {(block_i+1) / float(n_blocks) * 100.0:.1f}% done")
        offset = 0
        chunk_size = 1000 #fetch chunk_size results at a time. Max for subgraph=1000
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
                shares = float(d["shares"])
                if shares == 0.0: continue
                
                pool_addr = d["pool"]["id"]
                if pool_addr not in pool_dict: continue #if vol=0, purgatory, ..
                
                LP_addr = d["user"]["id"]
                if LP_addr.lower()  == SSBOT_address: continue #skip ss bot

                i = LP_dict[LP_addr]
                j = pool_dict[pool_addr]
                S[i,j] += shares / n_blocks
            offset += chunk_size
    
    #normalize
    for j in range(num_pools):
        S_pool = sum(S[:,j])
        assert S_pool > 0.0, "each pool should have stake"
        S[:,j] /= S_pool
    
    print("getStake(): done")
    return S

@enforce_types
def getConsumeVolumes(start_block:int, end_block:int,
                      subgraph_url:str) -> Dict[str, float]:
    """@return -- volumes -- dict of [DT_addr] -> consume_volume_in_OCEAN"""
    print("getConsumeVolumes(): begin")
    OCEAN_addr = oceanutil.OCEANtoken().address
    
    volumes = {}
    chunk_size = 1000 #max for subgraph = 1000
    for offset in range(0, end_block - start_block, chunk_size):
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
        """ % (start_block, end_block, offset, chunk_size)
        result = submitQuery(query, subgraph_url)
        new_orders = result["data"]["orders"]
        for order in new_orders:
            if (order["lastPriceToken"].lower() == OCEAN_addr.lower()):
                DT_addr = order["datatoken"]["id"]
                lastPriceValue = float(order["lastPriceValue"])
                if DT_addr not in volumes:
                    volumes[DT_addr] = 0.0
                volumes[DT_addr] += lastPriceValue
    
    print("getConsumeVolumes(): done")
    return volumes

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
            pool.nft_addr = d["datatoken"]["nft"]["id"] # tack this on
            pools.append(pool)
        
    return pools
        

