from typing import Dict, Union

from enforce_typing import enforce_types

from df_py.volume.reward_calc_main import RewardCalculator
from df_py.web3util.constants import ZERO_ADDRESS

# globals with compact names, to keep tests compact & readable
C1, C2, C3 = 7, 137, 1285  # chainIDs
NA, NB, NC, ND = "0xnfta_addr", "0xnftb_addr", "0xnftc_addr", "0xnftd_addr"
LP1, LP2, LP3, LP4 = "0xlp1_addr", "0xlp2_addr", "0xlp3_addr", "0xlp4_addr"
LP5 = "0xlp4_addr"
OCN_SYMB, H2O_SYMB = "OCEAN", "H2O"
OCN_ADDR, H2O_ADDR = "0xocean", "0xh2o"
OCN_ADDR2, H2O_ADDR2 = "0xocean2", "0xh2o2"
SYMBOLS = {
    C1: {OCN_ADDR: OCN_SYMB, H2O_ADDR: H2O_SYMB},
    C2: {OCN_ADDR2: OCN_SYMB, H2O_ADDR2: H2O_SYMB},
}
APPROVED_TOKEN_ADDRS = {C1: [OCN_ADDR, H2O_ADDR], C2: [OCN_ADDR2, H2O_ADDR2]}
DF_WEEK = 7
RATES = {"OCEAN": 0.5, "H2O": 1.6, "PSDN": 0.01}


# mock
class MockRewardCalculator(RewardCalculator):
    def __init__(self):
        return super().__init__({}, {}, {}, {}, {}, {}, DF_WEEK, False, False, False)

    def set_mock_attribute(self, attr_name, attr_value):
        setattr(self, attr_name, attr_value)

    def set_V_USD(self, V_USD):
        self.set_mock_attribute("V_USD", V_USD)


# ========================================================================
# Helpers to keep function calls compact, and return vals compact.


@enforce_types
def calc_rewards_C1(
    stakes: Dict[int, Dict[str, Dict[str, float]]],
    nftvols: Dict[int, Dict[str, Dict[str, float]]],
    OCEAN_avail: float,
    symbols: Dict[int, Dict[str, str]] = SYMBOLS,
    rates: Dict[str, float] = RATES,
    owners=None,
    df_week: int = DF_WEEK,
    do_pubrewards: bool = False,
    do_rank: bool = False,
):
    rewards_per_lp, rewards_info = _calc_rewards(
        stakes=stakes,
        locked_amts=stakes,  # pass veOCEAN stakes as locked_amts for simplicity
        nftvols=nftvols,
        OCEAN_avail=OCEAN_avail,
        symbols=symbols,
        rates=rates,
        owners=owners,
        df_week=df_week,
        do_pubrewards=do_pubrewards,
        do_rank=do_rank,
    )
    rewards_per_lp = {} if not rewards_per_lp else rewards_per_lp[C1]
    rewards_info = {} if not rewards_info else rewards_info[C1]
    return rewards_per_lp, rewards_info


@enforce_types
def _calc_rewards(
    stakes: Dict[int, Dict[str, Dict[str, float]]],
    locked_amts: Dict[int, Dict[str, Dict[str, float]]],
    nftvols: Dict[int, Dict[str, Dict[str, float]]],
    OCEAN_avail: float,
    symbols: Dict[int, Dict[str, str]] = SYMBOLS,
    rates: Dict[str, float] = RATES,
    owners=None,
    df_week: int = DF_WEEK,
    do_pubrewards: bool = False,
    do_rank: bool = False,
):
    """Helper. Fills in SYMBOLS, RATES, and DCV_multiplier for compactness"""
    if owners is None:
        owners = _null_owners(stakes, nftvols, symbols, rates)

    calculator = RewardCalculator(
        stakes,
        locked_amts,
        nftvols,
        owners,
        symbols,
        rates,
        df_week,
        OCEAN_avail,
        do_pubrewards,
        do_rank,
    )

    return calculator.calculate()


@enforce_types
def _null_owners(
    stakes: Dict[int, Dict[str, Dict[str, float]]],
    nftvols: Dict[int, Dict[str, Dict[str, float]]],
    symbols: Dict[int, Dict[str, str]] = SYMBOLS,
    rates: Dict[str, float] = RATES,
) -> Dict[int, Dict[str, Union[str, None]]]:
    """
    @return
      owners -- dict of [chainID][nft_addr] : ZERO_ADDRESS
    """
    calculator = RewardCalculator(
        stakes=stakes,
        locked_ocean_amts=stakes,
        nftvols=nftvols,
        owners={},
        symbols=symbols,
        rates=rates,
        df_week=DF_WEEK,
        OCEAN_avail=0.0,
        do_pubrewards=False,
        do_rank=False,
    )

    chain_nft_tups = calculator._get_chain_nft_tups()
    owners = _null_owners_from_chain_nft_tups(chain_nft_tups)
    return owners


@enforce_types
def _null_owners_from_chain_nft_tups(
    chain_nft_tups,
) -> Dict[int, Dict[str, Union[str, None]]]:
    """
    @arguments
      chain_nft_tups -- list of (chainID, nft_addr), indexed by j

    @return
      owners -- dict of [chainID][nft_addr] : ZERO_ADDRESS
    """
    owners = {}
    for chainID, nft_addr in chain_nft_tups:
        if chainID not in owners:
            owners[chainID] = {}
        owners[chainID][nft_addr] = ZERO_ADDRESS

    return owners
