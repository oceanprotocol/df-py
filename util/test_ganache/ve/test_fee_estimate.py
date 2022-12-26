import brownie
from enforce_typing import enforce_types
import pytest

from util import networkutil, oceanutil
from util.constants import BROWNIE_PROJECT as B
from util.base18 import toBase18, fromBase18
from datetime import datetime

accounts = None
alice = None
bob = None
veOCEAN = None
OCEAN = None
DAY = 86400
WEEK = 7 * 86400
MAXTIME = 4 * 365 * 86400  # 4 years
chain = brownie.network.chain
TA = toBase18(10000.0)
DAY = 86400


@enforce_types
def test_rewards():
    t0 = chain.time()
    t1 = t0 // WEEK * WEEK
    chain.sleep(t1 - t0)

    fee_distributor = B.FeeDistributor.deploy(
        veOCEAN.address,
        chain.time(),
        OCEAN.address,
        accounts[0].address,
        accounts[0].address,
        {
            "from": accounts[0],
        },
    )
    fee_distributor.toggle_allow_checkpoint_token({"from": accounts[0]})
    fee_estimate = B.FeeEstimate.deploy(
        veOCEAN.address,
        fee_distributor.address,
        {
            "from": accounts[0],
        },
    )
    # weekly , OPF adds 10 Ocean as rewards
    opffees = 10.0
    t0 = chain.time()

    OCEAN.approve(veOCEAN.address, toBase18(100.0), {"from": alice})
    OCEAN.approve(veOCEAN.address, toBase18(100.0), {"from": bob})

    # Alice locks OCEAN, Bob locks Ocean
    lock_time = t0 + 4 * 365 * 86400 - 15 * 60  # 4 years - 15 mins
    veOCEAN.create_lock(toBase18(100.0), lock_time, {"from": alice})
    veOCEAN.create_lock(toBase18(100.0), lock_time, {"from": bob})

    # make sure estimate returns 0, no reverts
    estimate = fee_estimate.estimateClaim(alice)
    assert estimate == 0

    # advance to the next week, without any checkpoints
    chain.sleep(WEEK)

    # top-up feeDistributor with some rewards, call checkpoint_token & checkpoint_total_supply
    OCEAN.transfer(fee_distributor.address, toBase18(opffees), {"from": accounts[0]})
    fee_distributor.checkpoint_token()
    fee_distributor.checkpoint_total_supply()

    # advance 25 hours, without any checkpoints
    chain.sleep(25 * 3600)
    chain.mine()

    # make sure estimate returns 0, no reverts
    estimate = fee_estimate.estimateClaim(alice)
    assert estimate == 0

    # advance to next week
    chain.sleep(WEEK - 25 * 3600)
    chain.mine()

    # checkpoint
    fee_distributor.checkpoint_token()
    fee_distributor.checkpoint_total_supply()

    # make sure estimates returns > 0
    estimate = fee_estimate.estimateClaim(alice)
    assert estimate > 0

    # Alice claims , make sure that claimed amount == estimated_reward from previous step
    before_balance = OCEAN.balanceOf(alice)
    fee_distributor.claim({"from": alice})
    after_balance = OCEAN.balanceOf(alice)
    assert after_balance - before_balance == estimate

    # advance 25 hours, without any checkpoints
    chain.sleep(25 * 3600)
    chain.mine()

    # make sure that Bob estimate_rewards >0 , no reverts
    estimate = fee_estimate.estimateClaim(bob)
    assert estimate > 0

    # make sure that Alice estimate_rewards = 0 , no reverts
    estimate = fee_estimate.estimateClaim(alice)
    assert estimate == 0


@enforce_types
def setup_function():
    global accounts, alice, bob, charlie, david, veOCEAN, OCEAN, feeDistributor
    networkutil.connect(networkutil.DEV_CHAINID)
    oceanutil.recordDevDeployedContracts()
    accounts = brownie.network.accounts

    alice = accounts.add()
    bob = accounts.add()
    charlie = accounts.add()
    david = accounts.add()

    OCEAN = oceanutil.OCEANtoken()
    veOCEAN = B.veOcean.deploy(
        OCEAN.address, "veOCEAN", "veOCEAN", "0.1.0", {"from": alice}
    )

    OCEAN.transfer(alice, TA, {"from": accounts[0]})
    OCEAN.transfer(bob, TA, {"from": accounts[0]})
    OCEAN.transfer(charlie, TA, {"from": accounts[0]})
    OCEAN.transfer(david, TA, {"from": accounts[0]})
