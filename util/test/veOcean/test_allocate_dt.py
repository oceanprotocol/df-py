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

    id1 = "23Bf9415c804fd777245CC2f7D9f141dd0AC34Ca-1"
    id2 = "9c0F7CEda17246514dBA4d65dCD93A37662B3bBa-137"
    id3 = "e447023dAC7A7DEB2e58d9b2f9b439D54e8Aa800-1"

    veAllocate.allocate(100, id1, {"from": accounts[0]})
    allocation = veAllocate.totalAllocation(accounts[0].address, 100, 0)
    assert allocation[0][0] == id1
    assert allocation[1][0] == 100

    veAllocate.allocate(25, id2, {"from": accounts[0]})
    allocation = veAllocate.totalAllocation(accounts[0].address, 100, 0)
    assert allocation[0][1] == id2
    assert allocation[1][1] == 25

    veAllocate.allocate(50, id3, {"from": accounts[0]})
    allocation = veAllocate.totalAllocation(accounts[0].address, 100, 0)
    assert allocation[0][2] == id3
    assert allocation[1][2] == 50

    # remove 50 tokens from id1
    veAllocate.removeAllocation(50, id1, {"from": accounts[0]})
    allocation = veAllocate.totalAllocation(accounts[0].address, 100, 0)
    assert allocation[0][0] == id1
    assert allocation[1][0] == 50

    # remove the remaining 50 tokens from id1
    veAllocate.removeAllocation(50, id1, {"from": accounts[0]})
    allocation = veAllocate.totalAllocation(accounts[0].address, 100, 0)
    assert allocation[0][0] == id3  # should swap with last one
    assert allocation[1][0] == 50  # should swap with last one


@enforce_types
def setup_function():
    networkutil.connect(networkutil.DEV_CHAINID)
    oceanutil.recordDevDeployedContracts()
    global accounts, veAllocate
    accounts = brownie.network.accounts
    veAllocate = B.veAllocate.deploy({"from": accounts[0]})
