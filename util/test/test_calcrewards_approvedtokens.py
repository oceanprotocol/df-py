import random
import time

from enforce_typing import enforce_types
import pytest
import brownie

from util import cleancase, networkutil, oceanutil, query
from util.calcrewards import calcRewards, _stakesToUsd, _poolvolsToUsd
from util.oceanutil import recordDeployedContracts, OCEAN_address
from util.constants import BROWNIE_PROJECT as B
from util.tok import TokSet

CHAINID = networkutil.DEV_CHAINID
ADDRESS_FILE = networkutil.chainIdToAddressFile(CHAINID)

# for shorter lines
C1, C2 = CHAINID, None
PA, PB, PC = "0xpoola_addr", "0xpoolb_addr", "0xpoolc_addr"
LP1, LP2, LP3, LP4 = "0xlp1_addr", "0xlp2_addr", "0xlp3_addr", "0xlp4_addr"
RATES = {"OCEAN": 0.5, "H2O": 1.6}

# these get filled on setup
OCN_ADDR, H2O_ADDR, APPROVED_TOKENS = None, None, None


@enforce_types
def test_stakesToUsd_unapprovedtoken():
    UNAPP = _deployTOK("UNAPP")
    UNAPP_addr = UNAPP.address.lower()
    stakes = {C1: {UNAPP_addr: {PA: {LP1: 3.0, LP2: 4.0}}}}
    stakes_USD = _stakesToUsd(stakes, RATES, APPROVED_TOKENS)
    assert stakes_USD == {C1: {}}


@enforce_types
def test_stakesToUsd_two_approved_one_unapproved():
    UNAPP = _deployTOK("UNAPP")
    UNAPP_addr = UNAPP.address.lower()

    stakes = {
        C1: {
            UNAPP_addr: {PA: {LP1: 3.0, LP2: 4.0}},
            OCN_ADDR: {PA: {LP1: 3.0, LP2: 4.0}},
            H2O_ADDR: {PC: {LP1: 5.0, LP4: 6.0}},
        }
    }
    stakes_USD = _stakesToUsd(stakes, RATES)
    assert stakes_USD == {
        C1: {
            PA: {LP1: 3.0 * 0.5, LP2: 4.0 * 0.5},
            PC: {LP1: 5.0 * 1.6, LP4: 6.0 * 1.6},
        }
    }


@enforce_types
def test_poolvolsToUsd_unapprovedtoken():
    UNAPP = _deployTOK("UNAPP")
    UNAPP_addr = UNAPP.address.lower()
    stakes = {C1: {UNAPP_addr: {PA: {LP1: 3.0, LP2: 4.0}}}}
    stakes_USD = _poolvolsToUsd(stakes, RATES)
    assert stakes_USD == {C1: {}}


@enforce_types
def test_poolvolsToUsd_two_approved_one_unapproved():
    UNAPP = _deployTOK("UNAPP")
    UNAPP_addr = UNAPP.address.lower()
    poolvols = {
        C1: {OCN_ADDR: {PA: 9.0, PB: 11.0}, H2O_ADDR: {PC: 13.0}, UNAPP_addr: {PC: 100}}
    }
    poolvols_USD = _poolvolsToUsd(poolvols, RATES)
    assert poolvols_USD == {
        C1: {
            PA: 9.0 * 0.5,
            PB: 11.0 * 0.5,
            PC: 13.0 * 1.6,
        }
    }


@enforce_types
def setup_function():
    """Setup any state tied to the execution of the given function.
    Invoked for every test function in the module.
    """
    global OCN_ADDR, H2O_ADDR, APPROVED_TOKENS
    
    networkutil.connect(CHAINID)
    recordDeployedContracts(ADDRESS_FILE)
    
    H2O = _deployTOK("H2O")
    
    OCN_ADDR = OCEAN_address().lower()
    H2O_ADDR = H2O.address.lower()

    #add H2O as approved token
    oceanutil.factoryRouter().addApprovedToken(H2O_ADDR, {"from": brownie.network.accounts[0]})

    #only proceed once subgraph sees H2O as approved (or we run out of time)
    time_slept = 0.0
    APPROVED_TOKENS = TokSet()
    loop_time, max_time_slept = 0.5, 20 
    while time_slept < max_time_slept and not APPROVED_TOKENS.hasAddress(CHAINID, H2O_ADDR):
        time.sleep(loop_time)
        time_slept += loop_time
        APPROVED_TOKENS = query.getApprovedTokens(CHAINID)
        print(f"time_slept = {time_slept}. # approved = {len(APPROVED_TOKENS.toks)}")
    assert APPROVED_TOKENS.hasAddress(CHAINID, H2O_ADDR), "need H2O as approved token"

@enforce_types
def _deployTOK(symbol: str):
    assert symbol == symbol.upper(), symbol
    return B.Simpletoken.deploy(
        f"{symbol}_{random.randint(0,99999):05d}", symbol, 18, 100e18,
        {"from": brownie.network.accounts[0]}
    )
