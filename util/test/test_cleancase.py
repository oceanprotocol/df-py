from enforce_typing import enforce_types
import pytest

from util import cleancase 

@enforce_types  
def test_stakes():
    stakes = {1: {"oCeAn": {"pOolA": {"Lp1": 1.0, "LP2": 2.0},
                            "POOLB": {"LP3": 3.0}},
                  "H2o": {"POoLC": {"lP4": 4.0}}},
              2: {"ocean": {"POOLD": {"LP5": 5.0}}}}
    target_stakes = {1: {"OCEAN": {"poola": {"lp1": 1.0, "lp2": 2.0},
                                   "poolb": {"lp3": 3.0}},
                         "H2O": {"poolc": {"lp4": 4.0}}},
                     2: {"ocean": {"poold": {"lp5": 5.0}}}}

    with pytest.raises(AssertionError):
        cleancase.assertStakes(stakes)
    
    mod_stakes = cleancase.modStakes(stakes)
    cleancase.assertStakes(mod_stakes)

    
