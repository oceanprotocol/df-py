import brownie
from enforce_typing import enforce_types
from util import networkutil, oceanutil

from util.constants import BROWNIE_PROJECT as B
from util.base18 import toBase18

accounts = None
veAllocate = None


@enforce_types
def test_allocate():
    """sending native tokens to dfrewards contract should revert"""

    veAllocate.setAllocation(100, "test", {"from": accounts[0]})
    allocation = veAllocate.totalAllocation(accounts[0].address)
    assert allocation[0] == 100
    assert allocation[1][0] == "test"
    assert allocation[2][0] == 100

    veAllocate.setAllocation(25, "test2", {"from": accounts[0]})
    allocation = veAllocate.totalAllocation(accounts[0].address)
    assert allocation[0] == 125
    assert allocation[1][1] == "test2"
    assert allocation[2][1] == 25

    veAllocate.setAllocation(50, "test3", {"from": accounts[0]})
    allocation = veAllocate.totalAllocation(accounts[0].address)
    assert allocation[0] == 175
    assert allocation[1][2] == "test3"
    assert allocation[2][2] == 50

    veAllocate.setAllocation(0, "test3", {"from": accounts[0]})
    allocation = veAllocate.totalAllocation(accounts[0].address)
    assert allocation[0] == 125
    assert allocation[1][2] == "test3"
    assert allocation[2][2] == 0


@enforce_types
def setup_function():
    networkutil.connect(networkutil.DEV_CHAINID)
    oceanutil.recordDevDeployedContracts()
    global accounts, veAllocate
    accounts = brownie.network.accounts
    veAllocate = B.veAllocate.deploy({"from": accounts[0]})
