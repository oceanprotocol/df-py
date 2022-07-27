import brownie
from enforce_typing import enforce_types
from util import networkutil, oceanutil

from util.constants import BROWNIE_PROJECT as B
import functools

accounts = None
veAllocate = None


@enforce_types
def test_allocate():
    """Allocate weight to different ids"""
    # Allocation is liquid, and based on weight.
    # Weight is arbitrary.
    # Weight is to be managed by sender.
    # Users do not need ve to use it. Checks sit on UX (contract spam => downstream vector).
    # Data Farming will use up to <100> allocations by id {DTNft}-{ChainID} per account.

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

    assert len(allocation[0]) == 3
    assert functools.reduce(lambda a, b: a + b, allocation[1]) == 175

    # Set allocation to 0 on id "test"
    # Drops it from array.
    # Triggers AllocationRemoved event
    veAllocate.setAllocation(0, "test", {"from": accounts[0]})
    allocation = veAllocate.getTotalAllocation(accounts[0].address, 100, 0)

    assert allocation[0][0] == "test3"
    assert allocation[1][0] == 50
    assert len(allocation[0]) == 2
    assert functools.reduce(lambda a, b: a + b, allocation[1]) == 75


@enforce_types
def setup_function():
    networkutil.connect(networkutil.DEV_CHAINID)
    global accounts, veAllocate
    accounts = brownie.network.accounts
    veAllocate = B.veAllocate.deploy({"from": accounts[0]})
