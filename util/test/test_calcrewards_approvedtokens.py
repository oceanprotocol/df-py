import random
import time

from enforce_typing import enforce_types
import pytest
import brownie

from util import oceanutil
from util.calcrewards import calcRewards, _stakesToUsd, _poolvolsToUsd
from util import cleancase
from util.oceanutil import recordDeployedContracts, OCEAN_address
from util.constants import BROWNIE_PROJECT as B
from util import networkutil
from util.query import getApprovedTokens

# for shorter lines
C1, C2 = networkutil.DEV_CHAINID, None
PA, PB, PC = "0xpoola_addr", "0xpoolb_addr", "0xpoolc_addr"
LP1, LP2, LP3, LP4 = "0xlp1_addr", "0xlp2_addr", "0xlp3_addr", "0xlp4_addr"
RATES = {"OCEAN": 0.5, "H2O": 1.6}

accounts = None
OCN, H2O = None, None


CHAINID = networkutil.DEV_CHAINID
ADDRESS_FILE = networkutil.chainIdToAddressFile(CHAINID)

@enforce_types
def test_stakesToUsd_nonapprovedtoken():
    unapproved_token = _deployTOK(accounts[0])
    unapproved_token_addr = unapproved_token.address.lower()
    stakes = {C1: {unapproved_token_addr: {PA: {LP1: 3.0, LP2: 4.0}}}}
    stakes_USD = _stakesToUsd(stakes, RATES)
    assert stakes_USD == {C1: {}}


@enforce_types
def test_stakesToUsd_two_approved_one_nonapproved():
    unapproved_token = _deployTOK(accounts[0])
    unapproved_token_addr = unapproved_token.address.lower()

    stakes = {
        C1: {
            unapproved_token_addr: {PA: {LP1: 3.0, LP2: 4.0}},
            OCN: {PA: {LP1: 3.0, LP2: 4.0}},
            H2O: {PC: {LP1: 5.0, LP4: 6.0}},
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
def test_poolvolsToUsd_nonapprovedtoken():
    unapproved_token = _deployTOK(accounts[0])
    unapproved_token_addr = unapproved_token.address.lower()
    stakes = {C1: {unapproved_token_addr: {PA: {LP1: 3.0, LP2: 4.0}}}}
    stakes_USD = _poolvolsToUsd(stakes, RATES)
    assert stakes_USD == {C1: {}}


@enforce_types
def test_poolvolsToUsd_two_approved_one_nonapproved():
    unapproved_token = _deployTOK(accounts[0])
    unapproved_token_addr = unapproved_token.address.lower()
    poolvols = {
        C1: {OCN: {PA: 9.0, PB: 11.0}, H2O: {PC: 13.0}, unapproved_token_addr: {PC: 100}}
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
    networkutil.connect(networkutil.DEV_CHAINID)
    global accounts
    accounts = brownie.network.accounts
    recordDeployedContracts(ADDRESS_FILE)

    global OCN, H2O
    OCN = OCEAN_address().lower()
    H2O = _deployTOK(accounts[0])
    H2O_addr = H2O.address.lower()

    approved_tokens = getApprovedTokens(networkutil.DEV_CHAINID)
    if H2O_addr not in approved_tokens.keys():
        oceanutil.factoryRouter().addApprovedToken(H2O_addr, {"from": accounts[0]})
        time.sleep(2)

    H2O = H2O_addr

@enforce_types
def _deployTOK(account):
    return B.Simpletoken.deploy(
        f"H2O_{random.randint(0,99999):05d}", "H2O", 18, 100e18, {"from": account}
    )
