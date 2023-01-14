import brownie
from enforce_typing import enforce_types
from util import networkutil, oceanutil

from util.constants import BROWNIE_PROJECT as B
import functools

accounts = None
veAllocate = None


@enforce_types
def test_getveAllocation():
    """getveAllocation should return the correct allocation."""
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
    """Test emitted events."""
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
    """Cannot set allocation above max."""
    nftaddr = accounts[1].address
    with brownie.reverts("Max Allocation"):
        veAllocate.setAllocation(10001, nftaddr, 1, {"from": accounts[0]})


@enforce_types
def test_getveBatchAllocation():
    """getveAllocation should return the correct allocation."""
    nftaddr1 = accounts[0].address
    nftaddr2 = accounts[1].address

    tx = veAllocate.setBatchAllocation(
        [50, 50], [nftaddr1, nftaddr2], [1, 1], {"from": accounts[0]}
    )
    assert veAllocate.getveAllocation(accounts[0], nftaddr1, 1) == 50
    assert veAllocate.getTotalAllocation(accounts[0]) == 100


@enforce_types
def test_batch_events():
    """Test emitted events."""
    nftaddr1 = accounts[1].address
    nftaddr2 = accounts[1].address
    tx = veAllocate.setBatchAllocation(
        [25, 75], [nftaddr1, nftaddr2], [1, 1], {"from": accounts[0]}
    )
    assert tx.events["AllocationSetMultiple"].values() == [
        accounts[0].address,
        [nftaddr1, nftaddr2],
        [1, 1],
        [25, 75],
    ]


@enforce_types
def test_batch_max_allocation():
    """Cannot set allocation above max."""
    nftaddr1 = accounts[1].address
    nftaddr2 = accounts[2].address
    with brownie.reverts("Max Allocation"):
        veAllocate.setBatchAllocation(
            [3500, 7500], [nftaddr1, nftaddr2], [1, 1], {"from": accounts[0]}
        )


@enforce_types
def test_batch_reverts():
    """Cannot have different lengths in arrays."""
    nftaddr1 = accounts[1].address
    nftaddr2 = accounts[2].address
    with brownie.reverts("Nft array size missmatch"):
        veAllocate.setBatchAllocation(
            [3500, 7500], [nftaddr1, nftaddr2, nftaddr2], [1, 1], {"from": accounts[0]}
        )
    with brownie.reverts("Chain array size missmatch"):
        veAllocate.setBatchAllocation(
            [3500, 7500], [nftaddr1, nftaddr2], [1], {"from": accounts[0]}
        )


@enforce_types
def setup_function():
    networkutil.connect(networkutil.DEV_CHAINID)
    global accounts, veAllocate
    accounts = brownie.network.accounts
    veAllocate = B.veAllocate.deploy({"from": accounts[0]})
