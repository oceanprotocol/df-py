from enforce_typing import enforce_types
from typing import Dict, Set, Tuple
from numpy import log10

@enforce_types
def calcRewards(stakes:dict, pool_vols:dict, rates:Dict[str,float],
                OCEAN_avail:float) -> Dict[str,float]:
    """
    @arguments
      stakes - dict of [basetoken_symbol][pool_addr][LP_addr] : stake
      pool_vols -- dict of [basetoken_symbol][pool_addr] : vol
      rates -- dict of [basetoken_symbol] : USD_per_basetoken
      OCEAN_avail -- float

    @return
      rewards -- dict of [LP_addr] : OCEAN_float

    A stake or vol value is denominated in basetoken (eg OCEAN, H2O).
    """
    stakes_USD, pool_vols_USD = _convertToUSD(stakes, pool_vols, rates)
    rewards = _calcRewardsUSD(stakes_USD, pool_vols_USD, OCEAN_avail)
    return rewards

def _convertToUSD(stakes:dict, pool_vols:dict, rates:Dict[str,float]) \
    -> Tuple[dict, dict]:
    """
    @description
      Converts stake and vol values from denomination in basetoken (eg OCEAN)
      to being denominated in USD. Then we can compare apples to apples.

    @arguments
      stakes - dict of [basetoken_symbol][pool_addr][LP_addr] : stake
      pool_vols -- dict of [basetoken_symbol][pool_addr] : vol
      rates -- dict of [basetoken_symbol] : USD_per_basetoken

    @return
      stakes_USD -- dict of [pool_addr][LP_addr] : stake_USD
      pool_vols_USD -- dict of [pool_addr] : vol_USD
    """
    stakes_USD = {} #dict of [pool_addr][LP_addr] : stake_USD
    pool_vols_USD = {} #dict of [pool_addr] : vol_USD

    for basetoken, rate in rates.items():
        if basetoken not in stakes: continue
        if basetoken not in pool_vols: continue
        
        for pool_addr in stakes[basetoken].keys():
            stakes_USD[pool_addr] = {}
            for LP_addr, stake in stakes[basetoken][pool_addr].items():
                stakes_USD[pool_addr][LP_addr] = stake * rate
        
        for pool_addr, vol in pool_vols[basetoken].items():
            pool_vols_USD[pool_addr] = vol * rate
            
    return (stakes_USD, pool_vols_USD)

def _calcRewardsUSD(stakes_USD:dict, pool_vols_USD:Dict[str,float],
                    OCEAN_avail:float) -> Dict[str, float]:
    """
    @arguments
      stakes_USD - dict of [pool_addr][LP_addr] : stake_USD
      pool_vols_USD -- dict of [pool_addr] : vol_USD
      OCEAN_avail -- float

    @return
      rewards -- dict of [LP_addr] : OCEAN_float
    """
    #base data
    pool_addrs = list(pool_vols_USD.keys())
    LP_addrs = list({addr for addrs in stakes_USD.values() for addr in addrs})
    
    #fill in R
    rewards = {} # [LP_addr] : OCEAN_float
    for i, LP_addr in enumerate(LP_addrs):
        reward_i = 0.0
        for j, pool_addr in enumerate(pool_addrs):
            if pool_addr not in stakes_USD: continue
            Sij = stakes_USD[pool_addr].get(LP_addr, 0.0)
            Cj = pool_vols_USD.get(pool_addr, 0.0)
            if Sij == 0 or Cj == 0: continue
            RF_ij = log10(Sij + 1.0) * log10(Cj + 2.0) #main formula!
            reward_i += RF_ij
        if reward_i > 0.0:
            rewards[LP_addr] = reward_i
            
    #normalize and scale rewards
    sum_ = sum(rewards.values())
    for LP_addr, reward in rewards.items():
        rewards[LP_addr] = reward / sum_ * OCEAN_avail

    #return dict
    return rewards
