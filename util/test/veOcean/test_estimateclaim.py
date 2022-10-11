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
    """Tests over 52 weeks for multiple users & cases if FeeEstimate.estimateClaim equals with the amount that you get after claim"""

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

    # each actor adds 100 Ocean tokens in week 0
    OCEAN.approve(veOCEAN.address, toBase18(100.0), {"from": alice})
    OCEAN.approve(veOCEAN.address, toBase18(100.0), {"from": bob})

    # each actor has different lock times
    alice_lock_time = t0 + 4 * 365 * 86400 - 15 * 60  # 4 years - 15 mins
    bob_lock_time = t0 + 2 * 365 * 86400 - 15 * 60  # 2 years - 15 mins
    veOCEAN.create_lock(toBase18(100.0), alice_lock_time, {"from": alice})
    veOCEAN.create_lock(toBase18(100.0), bob_lock_time, {"from": bob})

    alice_total_withdraws = 0
    bob_total_withdraws = 0
    rangeus = 52  # we will run the tests for 52 weeks
    sleep_amount = DAY * 7
    chain_time = datetime.utcfromtimestamp(chain.time()).strftime("%Y-%m-%d %H:%M:%S")
    print(f"Chain_time: {chain_time}")
    for i in range(rangeus):
        total_days = i * sleep_amount / DAY
        print(f"\nNew iteration****{i}****  Total days pased:{total_days}")
        chain.sleep(sleep_amount)
        chain.mine()
        chain_time = datetime.utcfromtimestamp(chain.time()).strftime(
            "%Y-%m-%d %H:%M:%S"
        )
        print(f"\t Chain_time after sleep: {chain_time}")

        # every week, OPC adds rewards
        print(f"\t OPF is adding {opffees} OCEAN as rewards")
        OCEAN.transfer(
            fee_distributor.address, toBase18(opffees), {"from": accounts[0]}
        )
        with brownie.reverts("Call checkpoint function"):
            fee_estimate.estimateClaimAcc(alice)
        fee_distributor.checkpoint_total_supply()
        with brownie.reverts("Call checkpoint function"):
            fee_estimate.estimateClaimAcc(alice)
        fee_distributor.checkpoint_token()
        epoch = veOCEAN.epoch()
        print(f"\t veOcean epoch: {epoch}")

        # fetch user data for all actors
        estimateAlice1w = fromBase18(fee_estimate.estimateClaim(alice))
        estimateBob1w = fromBase18(fee_estimate.estimateClaim(bob))
        epoch_alice = fee_distributor.user_epoch_of(alice)
        epoch_bob = fee_distributor.user_epoch_of(bob)
        time_cursor_alice = fee_distributor.time_cursor_of(alice)
        time_cursor_bob = fee_distributor.time_cursor_of(bob)
        time_cursor_alice_nice = datetime.utcfromtimestamp(time_cursor_alice).strftime(
            "%Y-%m-%d %H:%M:%S"
        )
        time_cursor_bob_nice = datetime.utcfromtimestamp(time_cursor_bob).strftime(
            "%Y-%m-%d %H:%M:%S"
        )

        print(
            f"\t Alice estimates claim:{estimateAlice1w}, Alice's epoch:{epoch_alice}, Alice's time cursor:{time_cursor_alice} = {time_cursor_alice_nice}"
        )
        # Alice claims every week
        initialAlice = fromBase18(OCEAN.balanceOf(alice))
        fee_distributor.claim({"from": alice})  # alice claims rewards
        afterAlice = fromBase18(OCEAN.balanceOf(alice))
        alice_claimed = afterAlice - initialAlice
        alice_total_withdraws = alice_total_withdraws + alice_claimed
        epoch_alice = fee_distributor.user_epoch_of(alice)
        time_cursor_alice = fee_distributor.time_cursor_of(alice)
        time_cursor_alice_nice = datetime.utcfromtimestamp(time_cursor_alice).strftime(
            "%Y-%m-%d %H:%M:%S"
        )
        # compare it
        print(
            f"\t Alice claimed:{alice_claimed}, After claim:  Alice's epoch:{epoch_alice}, Alice's time cursor:{time_cursor_alice} = {time_cursor_alice_nice}"
        )
        assert alice_claimed == pytest.approx(estimateAlice1w, 0.0000001)

        # Bob claims every 2 weeks
        print(
            f"\t Bob estimates claim:{estimateBob1w}, Bob's epoch:{epoch_bob}, Bob's time cursor:{time_cursor_bob} = {time_cursor_bob_nice}"
        )
        if i % 2 == 0:
            initialBob = fromBase18(OCEAN.balanceOf(bob))
            fee_distributor.claim({"from": bob})  # bob claims rewards
            afterBob = fromBase18(OCEAN.balanceOf(bob))
            bob_claimed = afterBob - initialBob
            bob_total_withdraws = bob_total_withdraws + bob_claimed
            epoch_bob = fee_distributor.user_epoch_of(bob)
            time_cursor_bob = fee_distributor.time_cursor_of(bob)
            time_cursor_bob_nice = datetime.utcfromtimestamp(time_cursor_bob).strftime(
                "%Y-%m-%d %H:%M:%S"
            )
            # compare it
            print(
                f"\t Bob claimed:{bob_claimed}, after claim Bob's epoch:{epoch_bob}, Bob's time cursor:{time_cursor_bob} = {time_cursor_bob_nice}"
            )
            assert bob_claimed == pytest.approx(estimateBob1w, 0.0000001)

        # Every 4 weeks, Bob is increasing his lock time, by adding one WEEk (+2 seconds)
        if i % 4 == 0:
            bob_lock_time = veOCEAN.locked__end(bob)
            veOCEAN.increase_unlock_time(bob_lock_time + WEEK + 2, {"from": bob})
            print(f"\t Bob increases the lock time")
            assert bob_claimed == pytest.approx(estimateBob1w, 0.0000001)

        fee_distributor_ocean_balance = fromBase18(
            OCEAN.balanceOf(fee_distributor.address)
        )
        fee_distributor_token_last_balance = fromBase18(
            fee_distributor.token_last_balance()
        )
        print(f"\n\t fee_distributor_ocean_balance:{fee_distributor_ocean_balance}")
        print(
            f"\t fee_distributor_token_last_balance:{fee_distributor_token_last_balance}"
        )
        assert fee_distributor_ocean_balance == pytest.approx(
            fee_distributor_token_last_balance, 0.0000001
        )

        print("end week********\n")


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
