import brownie
from enforce_typing import enforce_types
from util import networkutil, oceanutil

from util.constants import BROWNIE_PROJECT as B

accounts = None
veAllocate = None


@enforce_types
def test_get_total_allocation():
    """sending native tokens to dfrewards contract should revert"""
    nftaddr1 = accounts[0].address
    nftaddr2 = accounts[1].address
    nftaddr3 = accounts[2].address

    veAllocate.setAllocation(100, nftaddr1, 1, {"from": accounts[0]})
    assert veAllocate.getveAllocation(accounts[0], nftaddr1, 1) == 100

    veAllocate.setAllocation(25, nftaddr2, 1, {"from": accounts[0]})
    assert veAllocate.getveAllocation(accounts[0], nftaddr2, 1) == 25

    veAllocate.setAllocation(50, nftaddr3, 1, {"from": accounts[0]})
    assert veAllocate.getveAllocation(accounts[0], nftaddr3, 1) == 50

    veAllocate.setAllocation(0, nftaddr2, 1, {"from": accounts[0]})
    assert veAllocate.getveAllocation(accounts[0], nftaddr2, 1) == 0


@enforce_types
def test_events():
    nftaddr1 = accounts[1].address
    tx = veAllocate.setAllocation(100, nftaddr1, 1, {"from": accounts[0]})
    assert tx.events["AllocationSet"].values() == [
        accounts[0].address,
        accounts[1].address,
        1,
        100,
    ]


@enforce_types
def test_max_allocation():
    nftaddr = accounts[1].address
    with brownie.reverts("Max Allocation"):
        veAllocate.setAllocation(1001, nftaddr, 1, {"from": accounts[0]})


@enforce_types
def setup_function():
    networkutil.connect(networkutil.DEV_CHAINID)
    oceanutil.recordDevDeployedContracts()
    global accounts, veAllocate
    accounts = brownie.network.accounts
    veAllocate = B.veAllocate.deploy({"from": accounts[0]})
