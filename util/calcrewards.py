#Draws from https://github.com/oceanprotocol/df-js/blob/main/script/index.js

from enforce_typing import enforce_types
import json
import numpy
from numpy import log10
from pprint import pprint
import requests

from util import oceanutil
from util.blockrange import BlockRange
from util.oceanutil import calcDID
from util.graphutil import submitQuery

@enforce_types
def calcRewards(OCEAN_available:float, block_range:BlockRange,
                subgraph_url:str) -> dict:
    """ @return -- rewards -- dict of [LP_addr] : OCEAN_float"""
    print("calcRewards(): begin")
    print(f"  OCEAN_available: {OCEAN_available}")
    print(f"  block_range: {block_range}")
    
    pools = getPools(subgraph_url) #list of dict
    LP_list = getLPList(block_range, subgraph_url) #list [LP_i]:LP_addr

    C = getConsumeVolume(
        pools, block_range, subgraph_url) #array [pool_j]:OCEAN_float

    pool_list = [pool["id"] for pool in pools] #list [pool_j]:pool_addr
    
    S = getStake(
        LP_list, pool_list, block_range, subgraph_url) #array [LP_i,pool_j]:flt

    R = _calcRewardPerLP(C, S, OCEAN_available) #array [LP_i]:OCEAN_float

    rewards = {addr:R[i] for i,addr in enumerate(LP_list)}
    print("rewards: (OCEAN for each LP address)")
    pprint(rewards)

    print("calcRewards(): done")
    return rewards

@enforce_types
def getPools(subgraph_url:str):
    print("getPools(): begin")
    pools = getAllPools(subgraph_url)    
    pools = _filterToApprovedTokens(pools, subgraph_url)
    pools = _filterOutPurgatory(pools)
    print(f"  Got {len(pools)} pools")
    print("getPools(): done")
    return pools

@enforce_types
def getLPList(block_range:BlockRange, subgraph_url:str):
    """@return -- list of [LP_i] : LP_addr"""
    SSBOT_address = oceanutil.Staking().address.lower()
    LP_set = set()

    print("getLPList(): begin")
    n_blocks = block_range.numBlocks()
    for block_i, block in enumerate(block_range.getRange()):
        if (block_i % 50) == 0 or (block_i == n_blocks-1):
            print(f"  {(block_i+1) / float(n_blocks) * 100.0:.1f}% done")
        skip = 0
        INC = 1000 #fetch INC results at a time. Max for subgraph=1000
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
            """ % (skip, INC, block)
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
            skip += INC

    #set -> list
    LP_list = list(LP_set)

    print(f"  Got {len(LP_list)} LPs")
    print("getLPList(): done")
    return LP_list
   
@enforce_types
def _calcRewardPerLP(C, S, OCEAN_available:float):
    """
    @arguments
      C -- consume volumes - 1d array of [pool_j] : OCEAN_float
      S -- stake -- 1d array of [LP_i,pool_j] : share_float
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
def getStake(
        LP_list:list, pool_list:list, block_range:BlockRange, subgraph_url:str):
    """
    @arguments
      LP_list -- list of [LP_i] : LP_addr
      pool_list -- list of [pool_j] : pool_addr
      block_range -- BlockRange
      subgraph_url -- str

    @return
      S -- 2d array [LP_i, pool_j] : relative_stake_float -- stake in pool
    """
    print("getStake(): begin")
    SSBOT_address = oceanutil.Staking().address.lower()
    
    LP_dict = {addr:i for i,addr in enumerate(LP_list)} #[LP_addr]:LP_i
    pool_dict = {addr:j for j,addr in enumerate(pool_list)} #[pool_addr]:pool_j
    
    num_LPs, num_pools = len(LP_list), len(pool_list)
    S = numpy.zeros((num_LPs, num_pools), dtype=float)

    n_blocks = block_range.numBlocks()
    for block_i, block in enumerate(block_range.getRange()):
        if (block_i % 50) == 0 or (block_i == n_blocks-1):
            print(f"  {(block_i+1) / float(n_blocks) * 100.0:.1f}% done")
        skip = 0
        INC = 1000 #fetch INC results at a time. Max for subgraph=1000
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
            """ % (skip, INC, block)
            result = submitQuery(query, subgraph_url)
            new_pool_stake = result["data"]["poolShares"]
            if not new_pool_stake:
                break
            for d in new_pool_stake:
                LP_addr = d["user"]["id"]
                if LP_addr.lower()  == SSBOT_address: continue #skip ss bot
                
                shares = float(d["shares"])
                if shares == 0.0: continue
                pool_addr = d["pool"]["id"]
                i = LP_dict[LP_addr]
                j = pool_dict[pool_addr]
                S[i,j] += shares / n_blocks
            skip += INC
    
    #normalize
    for j in range(num_pools):
        S[:,j] /= sum(S[:,j])
    
    print("getStake(): done")
    return S
    
@enforce_types
def getConsumeVolume(pools:list, block_range:BlockRange, subgraph_url:str):
    """@return -- C -- 1d array of [pool_j] : OCEAN_float"""
    print("getConsumeVolume(): begin")
    num_pools = len(pools)
    C = numpy.zeros((num_pools,), dtype=float)
    for pool_j, pool in enumerate(pools):
        DT_addr = pool["datatoken"]["id"]
        (vol, _, _) = getConsumeVolumeAtDT(DT_addr, block_range, subgraph_url) 
        C[pool_j] = vol
    print("getConsumeVolume(): done")
    return C

@enforce_types
def getConsumeVolumeAtDT(DT_addr:str, block_range:BlockRange, subgraph_url:str):
    """
    @return 
      vol -- float -- consume volume (in OCEAN) for the given DT & block range
      num_consumes -- int
      lastPriceValues -- list of lastPriceValue_float
    """
    OCEAN_addr = oceanutil.OCEANtoken().address
    
    vol = 0.0
    num_consumes = 0
    lastPriceValues = []
    
    skip = 0
    INC = 1000 #fetch INC results at a time. Max for subgraph=1000
    while True:
        query = """
        {
          orders(where: {block_gte:%s, block_lte:%s, datatoken:"%s"}, 
                 skip:%s, first:%s) {
            id,
            datatoken {
              id
            },
            lastPriceToken,
            lastPriceValue,
            block
          }
        }
        """ % (block_range._start_block, block_range._end_block,
               DT_addr, skip, INC)
        result = submitQuery(query, subgraph_url)
        new_orders = result["data"]["orders"]
        if not new_orders:
            break
        for order in new_orders:
            if (order["lastPriceToken"].lower() == OCEAN_addr.lower()):
                lastPriceValue = float(order["lastPriceValue"])
                vol += lastPriceValue
                num_consumes += 1
                lastPriceValues.append(lastPriceValue)
        skip += INC

    return (vol, num_consumes, lastPriceValues)

@enforce_types
def _filterOutPurgatory(pools:list) -> list:
    """@return -- pools -- list of dict"""
    bad_dids = _didsInPurgatory()
    return [pool for pool in pools
            if calcDID(pool["datatoken"]["nft"]["id"]) not in bad_dids]

@enforce_types
def _didsInPurgatory() -> list:
    """return -- list of did (str)"""
    url = "https://raw.githubusercontent.com/oceanprotocol/list-purgatory/main/list-assets.json"
    resp = requests.get(url)

    #list of {'did' : 'did:op:6F7...', 'reason':'..'}
    data = json.loads(resp.text)

    return [item['did'] for item in data]
    
@enforce_types
def _filterToApprovedTokens(pools:list, subgraph_url:str) -> list:
    """@return -- pools -- list of dict"""
    approved_tokens = getApprovedTokens(subgraph_url) #list of str of addr
    assert approved_tokens, "no approved tokens"
    return [pool for pool in pools
            if pool['baseToken']['id'] in approved_tokens]

@enforce_types
def getApprovedTokens(subgraph_url:str) -> list:
    """@return -- token addresses -- list of str"""
    query = "{ opcs{approvedTokens} }"
    result = submitQuery(query, subgraph_url)
    return result['data']['opcs'][0]['approvedTokens']

@enforce_types
def getAllPools(subgraph_url:str) -> list:
    """@return -- pools -- list of dict (pool), where each pool is:
    {
      'id' : '0x..',
      'transactionCount' : '<e.g. 73>',
      'baseToken' : {'id' : '0x..'},
      'dataToken' : {'id' : '0x..', 'nft': {'id' : '0x..'},
    }
    """

    #since we don't know how many pools we have, fetch INC at a time
    # (1000 is max for subgraph)
    pools = []
    skip = 0
    INC = 1000
    while True:
        query = """
        {
          pools(skip:%s, first:%s){
            transactionCount,
            id
            datatoken {
                id,
                nft {
                    id
                }
            },
            baseToken {
                id
            }
          }
        }
        """ % (skip, INC)
        result = submitQuery(query, subgraph_url)
        new_pools = result['data']['pools']
        pools += new_pools
        if not new_pools:
            break
        skip += INC
    return pools
        

