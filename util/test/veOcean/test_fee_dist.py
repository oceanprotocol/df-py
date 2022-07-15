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
veOcean = None
ocean = None
feeDistributor = None
WEEK = 7 * 86400
MAXTIME = 4 * 365 * 86400  # 4 years
chain = brownie.network.chain
TA = 10e18


@enforce_types
def sleep_chain_week():
    t0 = chain.time()
    t1 = t0 // WEEK * WEEK
    chain.sleep(t1 - t0)


@enforce_types
def test_alice_locks_tokens():
    """sending native tokens to dfrewards contract should revert"""

    feeDistributor.checkpoint_token()
    feeDistributor.checkpoint_total_supply()
    chain.sleep(WEEK)

    veOcean.checkpoint()
    ocean.approve(veOcean.address, TA, {"from": alice})

    t0 = chain.time()
    t1 = t0 + WEEK * 5

    assert ocean.balanceOf(alice) != 0
    veOcean.create_lock(TA, t1, {"from": alice})
    assert ocean.balanceOf(alice) == 0

    chain.sleep(WEEK)

    ocean.transfer(feeDistributor.address, TA, {"from": accounts[0]})
    feeDistributor.checkpoint_token()
    feeDistributor.checkpoint_total_supply()

    chain.sleep(WEEK)

    ocean.transfer(feeDistributor.address, TA, {"from": accounts[0]})
    feeDistributor.checkpoint_token()
    feeDistributor.checkpoint_total_supply()

    chain.sleep(WEEK)

    assert feeDistributor.token_last_balance() == TA * 2

    before = veOcean.balanceOf(alice)
    feeDistributor.claim({"from": alice})  # alice claims rewards
    after = veOcean.balanceOf(alice)
    assert after > before


@enforce_types
def setup_function():
    global accounts, alice, bob, veOcean, ocean, feeDistributor
    networkutil.connect(networkutil.DEV_CHAINID)
    oceanutil.recordDevDeployedContracts()
    accounts = brownie.network.accounts

    alice = accounts.add()
    bob = accounts.add()

    ocean = oceanutil.OCEANtoken()
    veOcean = B.veOcean.deploy(
        ocean.address, "veOcean", "veOcean", "0.1.0", {"from": alice}
    )

    ocean.transfer(alice, TA, {"from": accounts[0]})
    ocean.transfer(bob, TA, {"from": accounts[0]})

    feeDistributor = B.FeeDistributor.deploy(
        veOcean.address,
        chain.time() // WEEK * WEEK,
        ocean.address,
        alice.address,
        alice.address,
        {
            "from": alice,
        },
    )
    sleep_chain_week()
