from enforce_typing import enforce_types
from numpy import log10

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
        reward_i = 0.0
        for j, pool_addr in enumerate(pool_addrs):
            if pool_addr not in stakes: continue
            Sij = stakes[pool_addr].get(LP_addr, 0.0)
            Cj = pool_vols.get(pool_addr, 0.0)
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
    print("_calcRewardPerLP(): done")
    return rewards
