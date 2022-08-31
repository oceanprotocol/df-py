import brownie
from enforce_typing import enforce_types


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
TA = toBase18(10.0)
DAY = 86400


@enforce_types
def test_alice_locks_tokens_after():
    """Alice locks tokens after fee distribution checkpoint. There should be no reward."""

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
    t0 = chain.time()
    t1 = t0 + WEEK * 10

    for _ in range(14):  # 2 weeks
        OCEAN.transfer(fee_distributor.address, TA, {"from": accounts[0]})
        fee_distributor.checkpoint_token()
        fee_distributor.checkpoint_total_supply()
        chain.sleep(DAY)
        chain.mine()

    chain.sleep(WEEK)
    chain.mine()

    assert fee_distributor.token_last_balance() == TA * 14

    assert OCEAN.balanceOf(alice) != 0
    OCEAN.approve(veOCEAN.address, TA, {"from": alice})
    veOCEAN.create_lock(TA, t1, {"from": alice})  # lock for 10 weeks
    assert OCEAN.balanceOf(alice) == 0
    chain.sleep(2 * WEEK)
    chain.mine()

    before_f = OCEAN.balanceOf(fee_distributor)
    before_a = veOCEAN.balanceOf(alice)
    fee_distributor.claim({"from": alice})  # alice claims rewards
    after_f = OCEAN.balanceOf(fee_distributor)
    after_a = veOCEAN.balanceOf(alice)
    assert after_f == before_f
    assert abs(after_a - before_a) < toBase18(0.01)


@enforce_types
def test_alice_locks_tokens_exact():
    """Alice locks tokens exactly at the time of fee distribution checkpoint. Alice then claim rewards."""

    veOCEAN.checkpoint()
    OCEAN.approve(veOCEAN.address, TA, {"from": alice})

    assert OCEAN.balanceOf(alice) != 0
    veOCEAN.create_lock(
        TA, chain[-1].timestamp + 8 * WEEK, {"from": alice}
    )  # lock for 8 weeks
    assert OCEAN.balanceOf(alice) == 0

    chain.sleep(WEEK)
    chain.mine()
    start_time = int(chain.time())
    chain.sleep(WEEK * 5)

    fee_distributor = B.FeeDistributor.deploy(
        veOCEAN.address,
        start_time,
        OCEAN.address,
        accounts[0].address,
        accounts[0].address,
        {
            "from": accounts[0],
        },
    )

    OCEAN.transfer(fee_distributor.address, TA, {"from": accounts[0]})
    fee_distributor.checkpoint_token()
    chain.sleep(WEEK)
    fee_distributor.checkpoint_token()

    before = OCEAN.balanceOf(fee_distributor)
    alice_before = veOCEAN.balanceOf(alice)
    fee_distributor.claim({"from": alice})  # alice claims rewards
    alice_after = veOCEAN.balanceOf(alice)

    assert (before - TA) < 10
    assert abs(alice_before * 2 - alice_after) < toBase18(1.0)


@enforce_types
def test_alice_claims_after_lock_ends():
    """Alice claim rewards after her lock is expired."""

    veOCEAN.checkpoint()
    OCEAN.approve(veOCEAN.address, TA, {"from": alice})

    assert OCEAN.balanceOf(alice) != 0
    veOCEAN.create_lock(
        TA, chain[-1].timestamp + 5 * WEEK, {"from": alice}
    )  # lock for 8 weeks
    assert OCEAN.balanceOf(alice) == 0

    chain.sleep(WEEK)
    chain.mine()
    start_time = int(chain.time())
    chain.sleep(WEEK * 1)

    fee_distributor = B.FeeDistributor.deploy(
        veOCEAN.address,
        start_time,
        OCEAN.address,
        accounts[0].address,
        accounts[0].address,
        {
            "from": accounts[0],
        },
    )

    OCEAN.transfer(fee_distributor.address, TA, {"from": accounts[0]})
    fee_distributor.checkpoint_token()
    chain.sleep(WEEK)
    fee_distributor.checkpoint_token()
    chain.sleep(WEEK * 5)
    veOCEAN.withdraw({"from": alice})

    before = OCEAN.balanceOf(fee_distributor)
    alice_balance_ve_before = veOCEAN.balanceOf(alice)
    fee_distributor.claim({"from": alice})  # alice claims rewards
    alice_balance_ocean = OCEAN.balanceOf(alice)
    alice_balance_ve_after = veOCEAN.balanceOf(alice)

    assert (before - TA) < 10
    assert alice_balance_ve_after == alice_balance_ve_before
    assert abs(alice_balance_ocean - TA * 2) < 10


@enforce_types
def setup_function():
    global accounts, alice, bob, veOCEAN, OCEAN, feeDistributor
    networkutil.connect(networkutil.DEV_CHAINID)
    oceanutil.recordDevDeployedContracts()
    accounts = brownie.network.accounts

    alice = accounts.add()
    bob = accounts.add()

    OCEAN = oceanutil.OCEANtoken()
    veOCEAN = B.veOcean.deploy(
        OCEAN.address, "veOCEAN", "veOCEAN", "0.1.0", {"from": alice}
    )

    OCEAN.transfer(alice, TA, {"from": accounts[0]})
    OCEAN.transfer(bob, TA, {"from": accounts[0]})
