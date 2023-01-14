import brownie
from enforce_typing import enforce_types
from pytest import approx


from util import networkutil, oceanutil
from util.constants import BROWNIE_PROJECT as B
from util.base18 import toBase18

deployer = None
veLocker = None
veOCEAN = None
smartWalletChecker = None
OCEAN = None
WEEK = 7 * 86400
MAXTIME = 4 * 365 * 86400  # 4 years
chain = brownie.network.chain
TA = toBase18(10.0)


@enforce_types
def test_velock_not_whitelisted():
    """Test that a smart contract cannot create a lock if they are not whitelisted."""
    smartWalletChecker.setAllowedContract(veLocker, False, {"from": deployer})
    assert smartWalletChecker.check(veLocker) == False

    with brownie.reverts("Smart contract depositors not allowed"):
        veLocker.create_lock(TA, chain.time() + WEEK * 2, {"from": deployer})


@enforce_types
def test_velock_whitelisted():
    """Test that a whitelisted contract can create a lock."""

    # Assert that the contract is whitelisted
    smartWalletChecker.setAllowedContract(veLocker, True, {"from": deployer})
    assert smartWalletChecker.check(veLocker) == True

    t0 = chain.time()
    t1 = t0 // WEEK * WEEK + WEEK
    t2 = t1 + WEEK
    chain.sleep(t1 - t0)

    assert OCEAN.balanceOf(veLocker) != 0
    veLocker.create_lock(TA, t2, {"from": deployer})
    assert OCEAN.balanceOf(veLocker) == 0

    epoch = veOCEAN.user_point_epoch(veLocker)
    assert epoch != 0

    assert veOCEAN.get_last_user_slope(veLocker) != 0
    veLockerVotingPower = (veOCEAN.balanceOf(veLocker, chain.time())) / toBase18(1.0)
    expectedVotingPower = (TA * WEEK / MAXTIME) / toBase18(1.0)
    assert veLockerVotingPower == approx(expectedVotingPower, 0.5)


@enforce_types
def setup_function():
    networkutil.connect(networkutil.DEV_CHAINID)
    oceanutil.recordDevDeployedContracts()
    global deployer, veOCEAN, OCEAN, veLocker, smartWalletChecker
    deployer = brownie.network.accounts[0]

    OCEAN = oceanutil.OCEANtoken()
    veOCEAN = B.veOcean.deploy(
        OCEAN.address, "veOCEAN", "veOCEAN", "0.1.0", {"from": deployer}
    )
    veLocker = B.veLocker.deploy(veOCEAN, OCEAN, {"from": deployer})
    OCEAN.transfer(veLocker, TA, {"from": deployer})
    smartWalletChecker = B.SmartWalletChecker.deploy({"from": deployer})

    # apply smart wallet checker
    veOCEAN.commit_smart_wallet_checker(smartWalletChecker.address, {"from": deployer})
    veOCEAN.apply_smart_wallet_checker({"from": deployer})
