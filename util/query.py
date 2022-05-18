import brownie
from enforce_typing import enforce_types
import json
import numpy
from numpy import log10
from pprint import pprint
import requests
from typing import Dict, List, Tuple

from util import oceanutil
from util.blockrange import BlockRange
from util.constants import BROWNIE_PROJECT as B
from util.graphutil import submitQuery


@enforce_types
class SimplePool:
    """
    A simple object to store pools retrieved from chain.
    Easier to retrieve info than using dicts keyed by strings, and
      more lightweight than a full BPool object.
    """
    def __init__(self, addr: str, nft_addr: str,
                 DT_addr: str, DT_symbol: str,
                 basetoken_addr: str):
        self.addr = addr
        self.nft_addr = nft_addr
        self.DT_addr = DT_addr
        self.DT_symbol = DT_symbol
        self.basetoken_addr = basetoken_addr

    @property
    def basetoken_symbol(self) -> str:
        return _symbol(self.basetoken_addr)

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
def query(rng: BlockRange, chainID: int) -> Tuple[list, dict, dict]:
    """
    @description
      Return pool info, stakes & poolvols, for the input block range and chain.

    @return
      pools_at_chain -- list of SimplePool
      stakes_at_chain -- dict of [basetoken_symbol][pool_addr][LP_addr] : stake
      poolvols_at_chain -- dict of [basetoken_symbol][pool_addr] : vol

    @notes
      A stake or poolvol value is in terms of basetoken (eg OCEAN, H2O).
      Basetoken symbols are full uppercase, addresses are full lowercase.
    """
    Pi = getPools(chainID)
    Si = getStakes(Pi, rng, chainID)
    Vi = getPoolVolumes(Pi, rng.st, rng.fin, chainID)
    return (Pi, Si, Vi)


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
      stakes_at_chain -- dict of [basetoken_symbol][pool_addr][LP_addr]:stake
    """
    print("getStakes(): begin")
    SSBOT_address = oceanutil.Staking().address.lower()
    stakes = {}
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
            result = submitQuery(query, chainID)
            new_pool_stake = result["data"]["poolShares"]
            if not new_pool_stake:
                break
            for d in new_pool_stake:
                basetoken_addr = d["pool"]["baseToken"]["id"].lower()
                basetoken_symbol = _symbol(basetoken_addr)
                pool_addr = d["pool"]["id"].lower()
                LP_addr = d["user"]["id"].lower()
                shares = float(d["shares"])
                if LP_addr == SSBOT_address:
                    continue  # skip ss bot

                if basetoken_symbol not in stakes:
                    stakes[basetoken_symbol] = {}
                if pool_addr not in stakes[basetoken_symbol]:
                    stakes[basetoken_symbol][pool_addr] = {}
                if LP_addr not in stakes[basetoken_symbol][pool_addr]:
                    stakes[basetoken_symbol][pool_addr][LP_addr] = 0.0

                stakes[basetoken_symbol][pool_addr][LP_addr] += shares/n_blocks
            offset += chunk_size

    return stakes #ie stakes_at_chain


@enforce_types
def getPoolVolumes(
        pools: list, st_block: int, end_block: int, chainID: int) -> dict:
    """
    @description
      Query the chain for pool volumes.

    @return
      poolvols_at_chain -- dict of [basetoken_symbol][pool_addr]:vol_amt
    """
    DT_vols = getDTVolumes(st_block, end_block, chainID)  # DT_addr : vol
    DTs_with_consume = set(DT_vols.keys())

    # dict of [basetoken_symbol][pool_addr] : vol
    poolvols = {}
    for pool in pools:
        if pool.DT_addr in DTs_with_consume:
            basetoken_symbol = _symbol(pool.basetoken_addr)
            if basetoken_symbol not in poolvols:
                poolvols[basetoken_symbol] = {}
            poolvols[basetoken_symbol][pool.addr] = DT_vols[pool.DT_addr]

    return poolvols #ie poolvols_at_chain


def getDTVolumes(st_block: int, end_block: int, chainID: int) \
    -> Dict[str, float]:
    """
    @description
      Return estimated datatoken (DT) volumes within given block range.

    @return
      DTvols_at_chain -- dict of [basetoken_symbol][DT_addr]:vol_amt
    """
    print("getDTVolumes(): begin")

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
        result = submitQuery(query, chainID)
        new_orders = result["data"]["orders"]
        for order in new_orders:
            DT_addr = order["datatoken"]["id"].lower()
            basetoken_addr = order["lastPriceToken"]
            basetoken_symbol = _symbol(basetoken_addr)
            if basetoken_symbol not in DT_vols:
                DT_vols[basetoken_symbol] = {}
                
            lastPriceValue = float(order["lastPriceValue"])
            if DT_addr not in DT_vols[basetoken_symbol]:
                DT_vols[basetoken_symbol][DT_addr] = 0.0
            DT_vols[basetoken_symbol][DT_addr] += lastPriceValue

    print("getDTVolumes(): done")
    return DT_vols #ie DTvols_at_chain


@enforce_types
def _filterOutPurgatory(pools: List[SimplePool], chainID:int) \
    -> List[SimplePool]:
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
        if oceanutil.calcDID(pool.nft_addr, chainID) not in bad_dids]
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
def getApprovedTokens(chainID: int) -> Dict[str, str]:
    """
    @description
      Return basetokens that are 'approved', ie eligible for data farming
    
    @return
      d - dict of [token_addr] : token_symbol
    """
    query = "{ opcs{approvedTokens} }"
    result = submitQuery(query, chainID)
    addrs = result["data"]["opcs"][0]["approvedTokens"]
    d = {addr.lower(): B.Simpletoken.at(addr).symbol().upper()
         for addr in addrs}
    assert len(addrs) == len(set(d.values())), "symbols not unique, eek"
    for symbol in d.values():
        assert symbol == symbol.upper(), "symbols should be uppercase"
    return d


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
        result = submitQuery(query, chainID)
        ds = result["data"]["pools"]
        for d in ds:
            tx_count = int(d["transactionCount"])
            if tx_count == 0:
                continue
            pool = SimplePool(
                addr=d["id"].lower(),
                nft_addr=d["datatoken"]["nft"]["id"].lower(),
                DT_addr=d["datatoken"]["id"].lower(),
                DT_symbol=d["datatoken"]["id"].upper(),
                basetoken_addr=d["baseToken"]["id"].lower(),
            )
            pools.append(pool)

    return pools


_ADDR_TO_SYMBOL = {} # address : TOKEN_symbol
def _symbol(addr:str):
    """Returns token symbol, given its address."""
    global _ADDR_TO_SYMBOL
    if addr not in _ADDR_TO_SYMBOL:
        symbol = B.Simpletoken.at(addr).symbol()
        symbol = symbol.upper() # follow lower-upper rules
        _ADDR_TO_SYMBOL[addr] = symbol
    return _ADDR_TO_SYMBOL[addr]

   
   
