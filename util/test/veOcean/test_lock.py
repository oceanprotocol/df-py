import time
import brownie
from enforce_typing import enforce_types
from pytest import approx


from util import networkutil, oceanutil
from util.constants import BROWNIE_PROJECT as B
from util.base18 import toBase18

accounts = None
alice = None
bob = None
veOCEAN = None
OCEAN = None
WEEK = 7 * 86400
MAXTIME = 4 * 365 * 86400  # 4 years
chain = brownie.network.chain
TA = 10e18


@enforce_types
def test_alice_locks_tokens():
    """sending native tokens to dfrewards contract should revert"""
    veOCEAN.checkpoint()
    OCEAN.approve(veOCEAN.address, TA, {"from": alice})

    t0 = chain.time()
    t1 = t0 // WEEK * WEEK + WEEK
    t2 = t1 + WEEK
    chain.sleep(t1 - t0)

    assert OCEAN.balanceOf(alice) != 0

    veOCEAN.create_lock(TA, t2, {"from": alice})

    assert OCEAN.balanceOf(alice) == 0

    epoch = veOCEAN.user_point_epoch(alice)
    assert epoch != 0

    assert veOCEAN.get_last_user_slope(alice) != 0
    aliceVotingPower = (veOCEAN.balanceOf(alice, chain.time())) / 1e18
    expectedVotingPower = (TA * WEEK / MAXTIME) / 1e18
    assert aliceVotingPower == approx(expectedVotingPower, 0.5)

    brownie.network.chain.sleep(t2)
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

    OCEAN = oceanutil.OCEANtoken()
    veOCEAN = B.veOcean.deploy(
        OCEAN.address, "veOCEAN", "veOCEAN", "0.1.0", {"from": alice}
    )

    OCEAN.transfer(alice, TA, {"from": accounts[0]})
    OCEAN.transfer(bob, TA, {"from": accounts[0]})
