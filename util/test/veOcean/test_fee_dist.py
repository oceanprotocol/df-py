import time
import brownie
from enforce_typing import enforce_types


from util import networkutil, oceanutil
from util.constants import BROWNIE_PROJECT as B
from util.base18 import toBase18

accounts = None
alice = None
bob = None
veOCEAN = None
ocean = None
WEEK = 7 * 86400
MAXTIME = 4 * 365 * 86400  # 4 years
chain = brownie.network.chain
TA = 10e18
DAY = 86400


@enforce_types
def test_alice_locks_tokens_after():
    """sending native tokens to dfrewards contract should revert"""

    fee_distributor = B.FeeDistributor.deploy(
        veOCEAN.address,
        chain.time(),
        ocean.address,
        accounts[0].address,
        accounts[0].address,
        {
            "from": accounts[0],
        },
    )

    ocean.approve(veOCEAN.address, TA, {"from": alice})

    t0 = chain.time()
    t1 = t0 + WEEK * 10

    for _ in range(14):  # 2 weeks
        ocean.transfer(fee_distributor.address, TA, {"from": accounts[0]})
        fee_distributor.checkpoint_token()
        fee_distributor.checkpoint_total_supply()
        chain.sleep(DAY)
        chain.mine()

    assert fee_distributor.token_last_balance() == TA * 14

    assert ocean.balanceOf(alice) != 0
    veOCEAN.create_lock(TA, t1, {"from": alice})  # lock for 10 weeks
    assert ocean.balanceOf(alice) == 0

    before = veOCEAN.balanceOf(alice)
    fee_distributor.claim({"from": alice})  # alice claims rewards
    after = veOCEAN.balanceOf(alice)
    assert after == before


@enforce_types
def test_alice_locks_tokens_exact():
    """sending native tokens to dfrewards contract should revert"""

    veOCEAN.checkpoint()
    ocean.approve(veOCEAN.address, TA, {"from": alice})

    assert ocean.balanceOf(alice) != 0
    veOCEAN.create_lock(
        TA, chain[-1].timestamp + 8 * WEEK, {"from": alice}
    )  # lock for 8 weeks
    assert ocean.balanceOf(alice) == 0

    chain.sleep(WEEK)
    chain.mine()
    start_time = int(chain.time())
    chain.sleep(WEEK * 5)

    fee_distributor = B.FeeDistributor.deploy(
        veOCEAN.address,
        start_time,
        ocean.address,
        accounts[0].address,
        accounts[0].address,
        {
            "from": accounts[0],
        },
    )

    ocean.transfer(fee_distributor.address, TA, {"from": accounts[0]})
    fee_distributor.checkpoint_token()
    chain.sleep(WEEK)
    fee_distributor.checkpoint_token()

    before = ocean.balanceOf(fee_distributor)
    alice_before = veOCEAN.balanceOf(alice)
    fee_distributor.claim({"from": alice})  # alice claims rewards
    alice_after = veOCEAN.balanceOf(alice)

    assert (before - TA) < 10
    assert abs(alice_before * 2 - alice_after) < 1e18


@enforce_types
def test_alice_claims_after_lock_ends():
    """sending native tokens to dfrewards contract should revert"""

    veOCEAN.checkpoint()
    ocean.approve(veOCEAN.address, TA, {"from": alice})

    assert ocean.balanceOf(alice) != 0
    veOCEAN.create_lock(
        TA, chain[-1].timestamp + 5 * WEEK, {"from": alice}
    )  # lock for 8 weeks
    assert ocean.balanceOf(alice) == 0

    chain.sleep(WEEK)
    chain.mine()
    start_time = int(chain.time())
    chain.sleep(WEEK * 1)

    fee_distributor = B.FeeDistributor.deploy(
        veOCEAN.address,
        start_time,
        ocean.address,
        accounts[0].address,
        accounts[0].address,
        {
            "from": accounts[0],
        },
    )

    ocean.transfer(fee_distributor.address, TA, {"from": accounts[0]})
    fee_distributor.checkpoint_token()
    chain.sleep(WEEK)
    fee_distributor.checkpoint_token()
    chain.sleep(WEEK * 5)
    veOCEAN.withdraw({"from": alice})

    before = ocean.balanceOf(fee_distributor)
    alice_balance_ve_before = veOCEAN.balanceOf(alice)
    fee_distributor.claim({"from": alice})  # alice claims rewards
    alice_balance_ocean = ocean.balanceOf(alice)
    alice_balance_ve_after = veOCEAN.balanceOf(alice)

    assert (before - TA) < 10
    assert alice_balance_ve_after == alice_balance_ve_before
    assert abs(alice_balance_ocean - TA * 2) < 10


@enforce_types
def setup_function():
    global accounts, alice, bob, veOCEAN, ocean, feeDistributor
    networkutil.connect(networkutil.DEV_CHAINID)
    oceanutil.recordDevDeployedContracts()
    accounts = brownie.network.accounts

    alice = accounts.add()
    bob = accounts.add()

    ocean = oceanutil.OCEANtoken()
    veOCEAN = B.veOCEAN.deploy(
        ocean.address, "veOCEAN", "veOCEAN", "0.1.0", {"from": alice}
    )

    ocean.transfer(alice, TA, {"from": accounts[0]})
    ocean.transfer(bob, TA, {"from": accounts[0]})
