import brownie
from enforce_typing import enforce_types
from util import networkutil, oceanutil

from util.constants import BROWNIE_PROJECT as B

accounts = None
veAllocate = None


@enforce_types
def test_allocate():
    """sending native tokens to dfrewards contract should revert"""

    veAllocate.setAllocation(100, "test", {"from": accounts[0]})
    allocation = veAllocate.getTotalAllocation(accounts[0].address, 100, 0)
    assert allocation[0][0] == "test"
    assert allocation[1][0] == 100

    veAllocate.setAllocation(25, "test2", {"from": accounts[0]})
    allocation = veAllocate.getTotalAllocation(accounts[0].address, 100, 0)
    assert allocation[0][1] == "test2"
    assert allocation[1][1] == 25

    veAllocate.setAllocation(50, "test3", {"from": accounts[0]})
    allocation = veAllocate.getTotalAllocation(accounts[0].address, 100, 0)
    assert allocation[0][2] == "test3"
    assert allocation[1][2] == 50

    veAllocate.setAllocation(0, "test", {"from": accounts[0]})
    allocation = veAllocate.getTotalAllocation(accounts[0].address, 100, 0)
    assert allocation[0][0] == "test3"
    assert allocation[1][0] == 50


@enforce_types
def setup_function():
    networkutil.connect(networkutil.DEV_CHAINID)
    oceanutil.recordDevDeployedContracts()
    global accounts, veAllocate
    accounts = brownie.network.accounts
    veAllocate = B.veAllocate.deploy({"from": accounts[0]})
