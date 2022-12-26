import functools

import brownie
from brownie.network import accounts
from enforce_typing import enforce_types

from util import networkutil, oceanutil
from util.base18 import toBase18


@enforce_types
def test_getveAllocation(ve_allocate):
    """getveAllocation should return the correct allocation."""
    nftaddr1 = accounts[0].address
    nftaddr2 = accounts[1].address
    nftaddr3 = accounts[2].address

    ve_allocate.setAllocation(100, nftaddr1, 1, {"from": accounts[0]})
    assert ve_allocate.getveAllocation(accounts[0], nftaddr1, 1) == 100

    ve_allocate.setAllocation(25, nftaddr2, 1, {"from": accounts[0]})
    assert ve_allocate.getveAllocation(accounts[0], nftaddr2, 1) == 25

    ve_allocate.setAllocation(50, nftaddr3, 1, {"from": accounts[0]})
    assert ve_allocate.getveAllocation(accounts[0], nftaddr3, 1) == 50

    ve_allocate.setAllocation(0, nftaddr2, 1, {"from": accounts[0]})
    assert ve_allocate.getveAllocation(accounts[0], nftaddr2, 1) == 0


@enforce_types
def test_events(ve_allocate):
    """Test emitted events."""
    nftaddr1 = accounts[1].address
    tx = ve_allocate.setAllocation(100, nftaddr1, 1, {"from": accounts[0]})
    assert tx.events["AllocationSet"].values() == [
        accounts[0].address,
        accounts[1].address,
        1,
        100,
    ]


@enforce_types
def test_getveBatchAllocation(ve_allocate):
    """getveAllocation should return the correct allocation."""
    alice = accounts.add()
    accounts[0].transfer(alice, toBase18(0.1)) #for gas fees
    
    nftaddr1 = accounts[0].address
    nftaddr2 = accounts[1].address

    tx = ve_allocate.setBatchAllocation(
        [50, 50], [nftaddr1, nftaddr2], [1, 1], {"from": alice}
    )
    assert ve_allocate.getveAllocation(alice, nftaddr1, 1) == 50
    assert ve_allocate.getveAllocation(alice, nftaddr2, 1) == 50
    assert ve_allocate.getTotalAllocation(alice) == 50 + 50


@enforce_types
def test_batch_events(ve_allocate):
    """Test emitted events."""
    nftaddr1 = accounts[1].address
    nftaddr2 = accounts[1].address
    tx = ve_allocate.setBatchAllocation(
        [25, 75], [nftaddr1, nftaddr2], [1, 1], {"from": accounts[0]}
    )
    assert tx.events["AllocationSetMultiple"].values() == [
        accounts[0].address,
        [nftaddr1, nftaddr2],
        [1, 1],
        [25, 75],
    ]

