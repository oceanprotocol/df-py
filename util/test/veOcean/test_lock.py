import brownie
from enforce_typing import enforce_types
import pytest
from pytest import approx


from util import networkutil, oceanutil
from util.constants import BROWNIE_PROJECT as B
from util.base18 import to_wei

accounts = None
alice = None
bob = None
veOCEAN = None
OCEAN = None
DAY = 86400
WEEK = 7 * DAY
YEAR = 365 * DAY
MAXTIME = 4 * YEAR
chain = brownie.network.chain
TA = to_wei(10.0)


@enforce_types
@pytest.mark.skip(reason="unskip once #575 fixed")
def test_alice_locks_tokens():
    """Lock tokens then check balance."""
    veOCEAN.checkpoint({"from": alice})
    OCEAN.approve(veOCEAN.address, TA, {"from": alice})

    t0 = chain.time()
    t1 = t0 // WEEK * WEEK + WEEK
    t2 = t1 + YEAR
    chain.sleep(t1 - t0)
    chain.mine()

    assert OCEAN.balanceOf(alice) != 0

    veOCEAN.create_lock(TA, t2, {"from": alice})

    assert OCEAN.balanceOf(alice) == 0

    epoch = veOCEAN.user_point_epoch(alice)
    assert epoch != 0

    assert veOCEAN.get_last_user_slope(alice) != 0
    aliceVotingPower = (veOCEAN.balanceOf(alice, chain.time())) / to_wei(1.0)
    expectedVotingPower = (TA * YEAR / MAXTIME) / to_wei(1.0)
    assert aliceVotingPower == approx(expectedVotingPower, 0.5)

    chain.sleep(t2 - t1)
    chain.mine()

    veOCEAN.withdraw({"from": alice})
    assert OCEAN.balanceOf(alice) == TA

    assert veOCEAN.get_last_user_slope(alice) == 0
    assert veOCEAN.balanceOf(alice, chain.time()) == 0


@enforce_types
def setup_function():
    networkutil.connect(networkutil.DEV_CHAINID)
    oceanutil.recordDevDeployedContracts()
    global accounts, alice, bob, veOCEAN, OCEAN
    accounts = brownie.network.accounts

    alice = accounts.add()
    bob = accounts.add()

    accounts[0].transfer(alice, "0.01 ether")
    accounts[0].transfer(bob, "0.01 ether")

    OCEAN = oceanutil.OCEANtoken()
    veOCEAN = B.veOcean.deploy(
        OCEAN.address, "veOCEAN", "veOCEAN", "0.1.0", {"from": alice}
    )

    OCEAN.transfer(alice, TA, {"from": accounts[0]})
    OCEAN.transfer(bob, TA, {"from": accounts[0]})
