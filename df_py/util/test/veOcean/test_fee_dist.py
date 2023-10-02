import os

import pytest
from enforce_typing import enforce_types
from eth_account import Account

from df_py.util import networkutil, oceanutil, oceantestutil
from df_py.util.base18 import to_wei
from df_py.util.contract_base import ContractBase

alice = None
bob = None
veOCEAN = None
OCEAN = None
WEEK = 7 * 86400
MAXTIME = 4 * 365 * 86400  # 4 years
chain = 8996
TA = to_wei(10.0)
DAY = 86400


@enforce_types
def test_alice_locks_tokens_after(account0):
    """Alice locks tokens after fee distribution checkpoint. There should be no reward."""

    fee_distributor = B.FeeDistributor.deploy(
        veOCEAN.address,
        chain.time(),
        OCEAN.address,
        account0.address,
        account0.address,
        {
            "from": account0,
        },
    )
    fee_estimate = B.FeeEstimate.deploy(
        veOCEAN.address,
        fee_distributor.address,
        {
            "from": account0,
        },
    )
    t0 = chain.time()
    t1 = t0 + WEEK * 10

    for _ in range(14):  # 2 weeks
        OCEAN.transfer(fee_distributor.address, TA, {"from": account0})
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
    try:
        estimate = fee_estimate.estimateClaim(alice)
    except:  # pylint: disable=bare-except
        estimate = None
    fee_distributor.claim({"from": alice})  # alice claims rewards
    after_f = OCEAN.balanceOf(fee_distributor)
    assert abs(after_f - before_f) < to_wei(0.01)
    if estimate is not None:
        assert abs(after_f - before_f) == estimate


@enforce_types
def test_alice_locks_tokens_exact():
    # pylint: disable=line-too-long
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
        accounts0.address,
        account0.address,
        {
            "from": account0,
        },
    )
    fee_estimate = B.FeeEstimate.deploy(
        veOCEAN.address,
        fee_distributor.address,
        {
            "from": account0,
        },
    )

    OCEAN.transfer(fee_distributor.address, TA, {"from": account0})
    fee_distributor.checkpoint_token()
    fee_distributor.checkpoint_total_supply()
    chain.sleep(WEEK)
    fee_distributor.checkpoint_token()
    fee_distributor.checkpoint_total_supply()

    alice_before = OCEAN.balanceOf(alice)
    try:
        estimate = fee_estimate.estimateClaim(alice)
    except:  # pylint: disable=bare-except
        estimate = None

    fee_distributor.claim({"from": alice})  # alice claims rewards
    alice_after = OCEAN.balanceOf(alice)

    assert (alice_before - TA) < 10
    assert alice_after > alice_before
    assert (alice_after - alice_before) == estimate


@pytest.mark.skip("Fails sometimes. See #705. When fixed, un-skip this test")
@enforce_types
def test_alice_claims_after_lock_ends(account0):
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
        account0.address,
        account0.address,
        {
            "from": account0,
        },
    )
    fee_estimate = B.FeeEstimate.deploy(
        veOCEAN.address,
        fee_distributor.address,
        {
            "from": account0,
        },
    )

    OCEAN.transfer(fee_distributor.address, TA, {"from": account0})
    fee_distributor.checkpoint_token()
    fee_distributor.checkpoint_total_supply()
    chain.sleep(WEEK)
    fee_distributor.checkpoint_token()
    fee_distributor.checkpoint_total_supply()
    chain.sleep(WEEK * 5)
    veOCEAN.withdraw({"from": alice})

    before = OCEAN.balanceOf(fee_distributor)
    alice_balance_ocean_before = OCEAN.balanceOf(alice)
    try:
        estimate = fee_estimate.estimateClaim(alice)
    except:  # pylint: disable=bare-except
        estimate = None
    fee_distributor.claim({"from": alice})  # alice claims rewards
    alice_balance_ocean_after = OCEAN.balanceOf(alice)

    assert (before - TA) < 10
    assert alice_balance_ocean_after > alice_balance_ocean_before
    assert abs(alice_balance_ocean_after - TA * 2) < 10
    if estimate is not None:
        assert (alice_balance_ocean_after - alice_balance_ocean_before) == estimate


@enforce_types
def setup_function():
    global alice, bob, veOCEAN, OCEAN
    oceanutil.record_dev_deployed_contracts()

    w3 = networkutil.chain_id_to_web3(8996)
    account0 = oceantestutil.get_account0()

    alice = w3.eth.account.create()
    bob = w3.eth.account.create()

    OCEAN = oceanutil.OCEAN_token()
    w3.eth.default_account = alice.address
    veOCEAN = ContractBase(
        w3,
        "ve/veOcean",
        constructor_args=[OCEAN.address, "veOCEAN", "veOCEAN", "0.1.0"],
    )

    OCEAN.transfer(alice, TA, {"from": account0})
    OCEAN.transfer(bob, TA, {"from": account0})
