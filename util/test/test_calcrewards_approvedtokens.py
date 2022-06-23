import random

from enforce_typing import enforce_types
import brownie

from util import networkutil, query
from util.calcrewards import _stakesToUsd, _poolvolsToUsd
from util.oceanutil import recordDeployedContracts, OCEAN_address
from util.constants import BROWNIE_PROJECT as B

CHAINID = networkutil.DEV_CHAINID
ADDRESS_FILE = networkutil.chainIdToAddressFile(CHAINID)

# for shorter lines
C1, C2 = CHAINID, None
PA, PB, PC = "0xpoola_addr", "0xpoolb_addr", "0xpoolc_addr"
LP1, LP2 = "0xlp1_addr", "0xlp2_addr"
RATES = {"OCEAN": 0.5, "UNAPP": 42.0}

# these get filled via setup_function
OCN_ADDR, APPROVED_TOKENS = None, None


@enforce_types
def test_stakesToUsd_unapprovedtoken():
    UNAPP = _deployTOK("UNAPP")
    UNAPP_ADDR = UNAPP.address.lower()
    stakes = {C1: {UNAPP_ADDR: {PA: {LP1: 3.0, LP2: 4.0}}}}
    stakes_USD = _stakesToUsd(stakes, RATES, APPROVED_TOKENS)
    assert stakes_USD == {C1: {}}


@enforce_types
def test_stakesToUsd_one_approved_one_unapproved():
    UNAPP = _deployTOK("UNAPP")
    UNAPP_ADDR = UNAPP.address.lower()

    stakes = {
        C1: {
            OCN_ADDR: {PA: {LP1: 1.1, LP2: 2.0}},
            UNAPP_ADDR: {PB: {LP1: 3.0, LP2: 4.0}},
        }
    }
    stakes_USD = _stakesToUsd(stakes, RATES, APPROVED_TOKENS)
    assert stakes_USD == {
        C1: {
            PA: {LP1: 1.1 * 0.5, LP2: 2.0 * 0.5},
        }
    }


@enforce_types
def test_poolvolsToUsd_unapprovedtoken():
    UNAPP = _deployTOK("UNAPP")
    UNAPP_ADDR = UNAPP.address.lower()
    stakes = {C1: {UNAPP_ADDR: {PA: {LP1: 3.0, LP2: 4.0}}}}
    stakes_USD = _poolvolsToUsd(stakes, RATES, APPROVED_TOKENS)
    assert stakes_USD == {C1: {}}


@enforce_types
def test_poolvolsToUsd_one_approved_one_unapproved():
    UNAPP = _deployTOK("UNAPP")
    UNAPP_ADDR = UNAPP.address.lower()
    poolvols = {
        C1: {
            OCN_ADDR: {PA: 9.0, PB: 11.0},
            UNAPP_ADDR: {PC: 15.0},
        }
    }
    poolvols_USD = _poolvolsToUsd(poolvols, RATES, APPROVED_TOKENS)
    assert poolvols_USD == {
        C1: {
            PA: 9.0 * 0.5,
            PB: 11.0 * 0.5,
        }
    }


@enforce_types
def setup_function():
    """Setup any state tied to the execution of the given function.
    Invoked for every test function in the module.
    """
    global OCN_ADDR, APPROVED_TOKENS

    networkutil.connect(CHAINID)
    recordDeployedContracts(ADDRESS_FILE)

    OCN_ADDR = OCEAN_address().lower()
    APPROVED_TOKENS = query.getApprovedTokens(CHAINID)


@enforce_types
def _deployTOK(symbol: str):
    assert symbol == symbol.upper(), symbol
    return B.Simpletoken.deploy(
        f"{symbol}_{random.randint(0,99999):05d}",
        symbol,
        18,
        100e18,
        {"from": brownie.network.accounts[0]},
    )
