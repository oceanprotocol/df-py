from typing import Dict

from enforce_typing import enforce_types


class RewardShaper:
    @staticmethod
    @enforce_types
    def flatten(rewards: Dict[int, Dict[str, float]]) -> Dict[str, float]:
        """
        @arguments
          rewards -- dict of [chainID][LP_addr] : reward_float

        @return
          flats -- dict of [LP_addr] : reward_float
        """
        flats: Dict[str, float] = {}
        for chainID in rewards:
            for LP_addr in rewards[chainID]:
                flats[LP_addr] = flats.get(LP_addr, 0.0) + rewards[chainID][LP_addr]

        return flats

    @staticmethod
    def merge(*reward_dicts):
        merged_dict = {}

        for reward_dict in reward_dicts:
            for key, value in reward_dict.items():
                merged_dict[key] = merged_dict.get(key, 0) + value

        return merged_dict


