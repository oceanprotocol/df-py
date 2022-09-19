import brownie
from enforce_typing import enforce_types
import pytest

from util import networkutil, oceanutil
from util.constants import BROWNIE_PROJECT as B
from util.base18 import toBase18, fromBase18

accounts = None
alice = None
bob = None
veOCEAN = None
OCEAN = None
WEEK = 7 * 86400
MAXTIME = 4 * 365 * 86400  # 4 years
chain = brownie.network.chain
TA = toBase18(10000.0)
DAY = 86400


@enforce_types
def test_rewards():
    """Test rewards, claims & feeEstimator"""

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
    #weekly , OPF adds 10 Ocean as rewards
    opffees = 10.0
    t0 = chain.time()

    # each actor adds 100 Ocean tokens in week 0
    OCEAN.approve(veOCEAN.address, toBase18(100.0), {"from": alice})
    OCEAN.approve(veOCEAN.address, toBase18(100.0), {"from": bob})
    OCEAN.approve(veOCEAN.address, toBase18(100.0), {"from": charlie})
    OCEAN.approve(veOCEAN.address, toBase18(100.0), {"from": david})
    
    # each actor has different lock times
    alice_lock_time = t0 + 4 * 365 * 86400 - 15*60 # 4 years - 15 mins
    bob_lock_time = t0 + 2 * 365 * 86400 - 15*60 # 2 years - 15 mins
    charlie_lock_time = t0 + 1 * 365 * 86400 - 15*60 # 1 year - 15 mins
    david_lock_time = t0 + 3 * 365 * 86400 - 15*60 # 3 year - 15 mins
    veOCEAN.create_lock(toBase18(100.0), alice_lock_time, {"from": alice})
    veOCEAN.create_lock(toBase18(100.0), bob_lock_time, {"from": bob})
    veOCEAN.create_lock(toBase18(100.0), charlie_lock_time, {"from": charlie})
    veOCEAN.create_lock(toBase18(100.0), david_lock_time, {"from": david})
    
    #wait 2 days and OPF adds rewards
    chain.sleep(DAY)
    chain.mine()
    chain.sleep(DAY)
    chain.mine()
    OCEAN.transfer(fee_distributor.address, toBase18(opffees), {"from": accounts[0]})
    fee_distributor.checkpoint_token()
    fee_distributor.checkpoint_total_supply()
    # and sleep one more day
    chain.sleep(DAY)
    chain.mine()

    alice_total_withdraws=0
    bob_total_withdraws=0
    charlie_total_withdraws=0
    david_total_withdraws=0
    rangeus=52  # we will run the tests for 1 year
    for i in range(rangeus):  
        print(f"\nNew week****{i}****")
        chain.sleep(WEEK)
        chain.mine()
        
        print(f"\t OPF is adding {opffees} as rewards")
        OCEAN.transfer(fee_distributor.address, toBase18(opffees), {"from": accounts[0]})
        fee_distributor.checkpoint_token()
        fee_distributor.checkpoint_total_supply()
        
        
        # compute estimateClaim
        estimateAlice1w = fromBase18(fee_estimate.estimateClaim(alice))
        estimateBob1w = fromBase18(fee_estimate.estimateClaim(bob))
        estimateCharlie1w = fromBase18(fee_estimate.estimateClaim(charlie))
        estimateDavid1w = fromBase18(fee_estimate.estimateClaim(david))
        print(f"\t Alice estimates claim:{estimateAlice1w}")
        
        
        # Alice claims every week
        initialAlice=fromBase18(OCEAN.balanceOf(alice))
        fee_distributor.claim({"from": alice})  # alice claims rewards
        afterAlice=fromBase18(OCEAN.balanceOf(alice))
        alice_claimed = afterAlice-initialAlice
        alice_total_withdraws=alice_total_withdraws+alice_claimed
        #compare it
        print(f"\t Alice claimed:{alice_claimed}")
        assert alice_claimed == pytest.approx(estimateAlice1w,0.0000001)

        # Bob claims every 2 weeks
        print(f"\t Bob estimates claim:{estimateBob1w}")
        if i%2==0:
            initialBob=fromBase18(OCEAN.balanceOf(bob))
            fee_distributor.claim({"from": bob})  # bob claims rewards
            afterBob=fromBase18(OCEAN.balanceOf(bob))
            bob_claimed = afterBob-initialBob
            bob_total_withdraws=bob_total_withdraws+bob_claimed
            #compare it
            print(f"\t Bob claimed:{bob_claimed}")
            assert bob_claimed == pytest.approx(estimateBob1w,0.0000001)

        print("end week********\n")

    assert fee_distributor.token_last_balance() == 2 #this fails, to see the print statements :)

    


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
