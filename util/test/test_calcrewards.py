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

RATES = None
accounts = None
# for shorter lines
C1, C2 = networkutil.DEV_CHAINID, None
PA, PB, PC = "poola_addr", "poolb_addr", "poolc_addr"
LP1, LP2, LP3, LP4 = "lp1_addr", "lp2_addr", "lp3_addr", "lp4_addr"
OCN, H2O = None, None

CHAINID = networkutil.DEV_CHAINID
ADDRESS_FILE = networkutil.chainIdToAddressFile(CHAINID)


@enforce_types
def test_calcRewards1_onechain():
    stakes = {C1: {OCN: {PA: {LP1: 10000.0}}}}
    poolvols = {C1: {OCN: {PA: 1.0}}}

    target_rewardsperlp = {C1: {LP1: 10.0}}
    target_rewardsinfo = {C1: {PA: {LP1: 10}}}

    TOKEN_avail = 10.0
    rewardsperlp, rewardsinfo = calcRewards(stakes, poolvols, RATES, TOKEN_avail)

    assert target_rewardsperlp == rewardsperlp
    assert target_rewardsinfo == rewardsinfo


@enforce_types
def test_calcRewards1_twochains():
    # Cannot test two chains because ganache is the only local chain.
    pytest.skip("Cannot test two chains")
    stakes = {C1: {OCN: {PA: {LP1: 10000.0}}}, C2: {OCN: {PB: {LP1: 10000.0}}}}
    poolvols = {C1: {OCN: {PA: 1.0}}, C2: {OCN: {PB: 1.0}}}
    rewardsperlp, rewardsinfo = calcRewards(stakes, poolvols, RATES, TOKEN_avail=20.0)
    assert rewardsperlp == {C1: {LP1: 10.0}, C2: {LP1: 10.0}}
    assert rewardsinfo == {
        C1: {
            PA: {LP1: 10.0},
        },
        C2: {PB: {LP1: 10.0}},
    }


@enforce_types
def test_calcRewards2():
    stakes = {C1: {OCN: {PA: {LP1: 10000.0, LP2: 10000.0}}}}
    poolvols = {C1: {OCN: {PA: 1.0}}}
    rewardsperlp, rewardsinfo = calcRewards(stakes, poolvols, RATES, TOKEN_avail=10.0)
    assert sum(rewardsperlp[C1].values()) == pytest.approx(10.0, 0.01)
    assert sum(rewardsinfo[C1][PA].values()) == pytest.approx(10.0, 0.01)
    assert rewardsperlp == {C1: {LP1: 5.0, LP2: 5.0}}
    assert rewardsinfo == {C1: {PA: {LP1: 5.0, LP2: 5.0}}}


@enforce_types
def test_calcRewards3():
    stakes = {
        C1: {OCN: {PA: {LP1: 10000.0, LP2: 10000.0}, PB: {LP1: 10000.0, LP3: 10000.0}}}
    }
    poolvols = {C1: {OCN: {PA: 1.0}}}  # P1 has volume, but not P2
    rewardsperlp, rewardsinfo = calcRewards(stakes, poolvols, RATES, TOKEN_avail=10.0)
    assert sum(rewardsperlp[C1].values()) == pytest.approx(10.0, 0.01)
    assert min(rewardsperlp[C1].values()) > 0, "shouldn't have entries with 0 rewards"
    assert rewardsperlp == {C1: {LP1: 5.0, LP2: 5.0}}

    assert sum(rewardsinfo[C1][PA].values()) == pytest.approx(10.0, 0.01)
    assert (
        min(rewardsinfo[C1][PA].values()) > 0
    ), "shouldn't have entries with 0 rewards"
    assert rewardsinfo == {C1: {PA: {LP1: 5.0, LP2: 5.0}}}


@enforce_types
def test_calcRewards4():
    stakes = {
        C1: {OCN: {PA: {LP1: 10000.0, LP2: 10000.0}, PB: {LP1: 10000.0, LP3: 10000.0}}}
    }
    poolvols = {C1: {OCN: {PA: 1.0, PB: 1.0}}}  # P1 & P2 both have volume
    rewardsperlp, rewardsinfo = calcRewards(stakes, poolvols, RATES, TOKEN_avail=10.0)
    assert sum(rewardsperlp[C1].values()) == pytest.approx(10.0, 0.01)
    assert rewardsperlp == {C1: {LP1: 5.0, LP2: 2.5, LP3: 2.5}}

    assert sum(rewardsinfo[C1][PA].values()) == pytest.approx(5.0, 0.01)
    assert sum(rewardsinfo[C1][PB].values()) == pytest.approx(5.0, 0.01)
    assert rewardsinfo == {C1: {PA: {LP1: 2.5, LP2: 2.5}, PB: {LP1: 2.5, LP3: 2.5}}}


@enforce_types
def test_calcRewards5_mix_upper_and_lower_case():
    # PA, PB, PC = "poola_addr", "poolb_addr", "poolc_addr"
    # LP1, LP2, LP3, LP4 = "lp1_addr", "lp2_addr", "lp3_addr", "lp4_addr"
    # OCN, H2O = "OCEAN", "H2O"

    stakes = {C1: {OCN: {PA: {LP1: 10000.0}}}}
    stakes2a = {C1: {OCN.upper(): {PA: {LP1: 10000.0}}}}
    stakes2b = {C1: {OCN: {"pOoLa_aDDr": {LP1: 10000.0}}}}
    stakes2c = {C1: {OCN: {PA: {"lP1_aDdR": 10000.0}}}}

    poolvols = {C1: {OCN: {PA: 10000.0}}}
    poolvols2a = {C1: {OCN.upper(): {PA: 10000.0}}}
    poolvols2b = {C1: {OCN: {"pOola_adDr": 10000.0}}}

    rates = {"OCEAN": 0.5, "H2O": 1.6}
    rates2 = {"oceaN": 0.5, "h2O": 1.6}

    target_rewardsperlp = {C1: {LP1: 10.0}}
    target_rewardsinfo = {C1: {PA: {LP1: 10.0}}}
    TOKEN_avail = 10.0

    # sanity check
    cleancase.assertStakes(stakes)
    cleancase.assertPoolvols(poolvols)
    cleancase.assertRates(rates)

    # the real tests
    rewardsperlp, rewardsinfo = calcRewards(stakes2a, poolvols, rates, TOKEN_avail)
    assert target_rewardsperlp == rewardsperlp
    assert target_rewardsinfo == rewardsinfo

    rewardsperlp, _ = calcRewards(stakes2b, poolvols, rates, TOKEN_avail)
    assert target_rewardsperlp == rewardsperlp
    assert target_rewardsinfo == rewardsinfo

    rewardsperlp, _ = calcRewards(stakes2c, poolvols, rates, TOKEN_avail)
    assert target_rewardsperlp == rewardsperlp
    assert target_rewardsinfo == rewardsinfo

    rewardsperlp, _ = calcRewards(stakes, poolvols2a, rates, TOKEN_avail)
    assert target_rewardsperlp == rewardsperlp
    assert target_rewardsinfo == rewardsinfo

    rewardsperlp, _ = calcRewards(stakes, poolvols2b, rates, TOKEN_avail)
    assert target_rewardsperlp == rewardsperlp
    assert target_rewardsinfo == rewardsinfo

    rewardsperlp, _ = calcRewards(stakes, poolvols, rates2, TOKEN_avail)
    assert target_rewardsperlp == rewardsperlp
    assert target_rewardsinfo == rewardsinfo


def test_calcrewards_math():
    ## update this test when the reward function is changed

    stakes = {C1: {OCN: {PA: {LP1: 20000, LP2: 50000}, PB: {LP1: 20000, LP3: 10000}}}}
    poolvols = {C1: {OCN: {PA: 32.0, PB: 8.0}}}
    rewardsperlp, rewardsinfo = calcRewards(stakes, poolvols, RATES, TOKEN_avail=100.0)

    assert sum(rewardsperlp[C1].values()) == pytest.approx(100.0, 0.01)
    assert rewardsperlp[C1][LP1] == pytest.approx(33.37, 0.01)
    assert rewardsperlp[C1][LP2] == pytest.approx(62.49, 0.01)
    assert rewardsperlp[C1][LP3] == pytest.approx(4.16, 0.01)

    assert rewardsinfo[C1][PA][LP1] == pytest.approx(25.0, 0.01)
    assert rewardsinfo[C1][PA][LP2] == pytest.approx(62.49, 0.01)
    assert rewardsinfo[C1][PB][LP1] == pytest.approx(8.33, 0.01)
    assert rewardsinfo[C1][PB][LP3] == pytest.approx(4.16, 0.01)


def test_apy_cap():
    stakes = {C1: {OCN: {PA: {LP1: 1000 / 0.0015717}}}}
    poolvols = {C1: {OCN: {PA: 1.0}}}

    target_rewardsperlp = {C1: {LP1: 1000.0}}
    target_rewardsinfo = {C1: {PA: {LP1: 1000}}}

    TOKEN_avail = 700_000.0
    rewardsperlp, rewardsinfo = calcRewards(stakes, poolvols, RATES, TOKEN_avail)

    assert target_rewardsperlp == rewardsperlp
    assert target_rewardsinfo == rewardsinfo


@enforce_types
def test_stakesToUsd_onebasetoken():
    stakes = {C1: {OCN: {PA: {LP1: 3.0, LP2: 4.0}}}}
    stakes_USD = _stakesToUsd(stakes, RATES)
    assert stakes_USD == {C1: {PA: {LP1: 3.0 * 0.5, LP2: 4.0 * 0.5}}}


@enforce_types
def test_stakesToUsd_nonapprovedtoken():
    nonApprovedToken = _deployTOK(accounts[0])
    nonApprovedTokenAddr = nonApprovedToken.address.lower()
    stakes = {C1: {nonApprovedTokenAddr: {PA: {LP1: 3.0, LP2: 4.0}}}}
    stakes_USD = _stakesToUsd(stakes, RATES)
    assert stakes_USD == {C1: {}}


@enforce_types
def test_stakesToUsd_two_approved_one_nonapproved():
    nonApprovedToken = _deployTOK(accounts[0])
    nonApprovedTokenAddr = nonApprovedToken.address.lower()

    stakes = {
        C1: {
            nonApprovedTokenAddr: {PA: {LP1: 3.0, LP2: 4.0}},
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
def test_stakesToUsd_twobasetokens():
    stakes = {
        C1: {
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
def test_poolvolsToUsd_onebasetoken():
    poolvols = {C1: {OCN: {PA: 9.0, PB: 11.0}}}
    poolvols_USD = _poolvolsToUsd(poolvols, RATES)
    assert poolvols_USD == {C1: {PA: 9.0 * 0.5, PB: 11.0 * 0.5}}


@enforce_types
def test_poolvolsToUsd_nonapprovedtoken():
    nonApprovedToken = _deployTOK(accounts[0])
    nonApprovedTokenAddr = nonApprovedToken.address.lower()
    stakes = {C1: {nonApprovedTokenAddr: {PA: {LP1: 3.0, LP2: 4.0}}}}
    stakes_USD = _poolvolsToUsd(stakes, RATES)
    assert stakes_USD == {C1: {}}


@enforce_types
def test_poolvolsToUsd_two_approved_one_nonapproved():
    nonApprovedToken = _deployTOK(accounts[0])
    nonApprovedTokenAddr = nonApprovedToken.address.lower()
    poolvols = {
        C1: {OCN: {PA: 9.0, PB: 11.0}, H2O: {PC: 13.0}, nonApprovedTokenAddr: {PC: 100}}
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
def test_poolvolsToUsd_twobasetokens():
    poolvols = {C1: {OCN: {PA: 9.0, PB: 11.0}, H2O: {PC: 13.0}}}
    poolvols_USD = _poolvolsToUsd(poolvols, RATES)
    assert poolvols_USD == {
        C1: {
            PA: 9.0 * 0.5,
            PB: 11.0 * 0.5,
            PC: 13.0 * 1.6,
        }
    }


@enforce_types
def _deployTOK(account):
    return B.Simpletoken.deploy(
        f"H2O_{random.randint(0,99999):05d}", "H2O", 18, 100e18, {"from": account}
    )


@enforce_types
def setup_function():
    networkutil.connect(networkutil.DEV_CHAINID)
    global accounts
    accounts = brownie.network.accounts
    recordDeployedContracts(ADDRESS_FILE)

    global OCN, H2O
    OCN = OCEAN_address().lower()
    H2O = _deployTOK(accounts[0])
    H2O_addr = H2O.address.lower()

    approvedTokens = getApprovedTokens(networkutil.DEV_CHAINID)
    if H2O_addr not in approvedTokens.keys():
        oceanutil.factoryRouter().addApprovedToken(H2O_addr, {"from": accounts[0]})
        time.sleep(2)

    global RATES
    RATES = {"OCEAN": 0.5, H2O.symbol(): 1.6}
    H2O = H2O_addr
