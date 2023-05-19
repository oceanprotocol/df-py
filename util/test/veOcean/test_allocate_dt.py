import random
import time

import brownie
from enforce_typing import enforce_types
import pytest

from util import oceanutil
from util.constants import BROWNIE_PROJECT as B
import functools

accounts = None
veAllocate = None


@enforce_types
def test_getveAllocation():
    """getveAllocation should return the correct allocation."""
    nft_addrs = [_rnd_addr() for i in range(3)]

    veAllocate.setAllocation(100, nft_addrs[0], 1, {"from": accounts[0]})
    assert veAllocate.getveAllocation(accounts[0], nft_addrs[0], 1) == 100

    veAllocate.setAllocation(25, nft_addrs[1], 1, {"from": accounts[0]})
    assert veAllocate.getveAllocation(accounts[0], nft_addrs[1], 1) == 25

    veAllocate.setAllocation(50, nft_addrs[2], 1, {"from": accounts[0]})
    assert veAllocate.getveAllocation(accounts[0], nft_addrs[2], 1) == 50

    veAllocate.setAllocation(0, nft_addrs[1], 1, {"from": accounts[0]})
    assert veAllocate.getveAllocation(accounts[0], nft_addrs[1], 1) == 0


@enforce_types
def test_events():
    """Test emitted events."""
    nft_addr = _rnd_addr()

    tx = veAllocate.setAllocation(100, nft_addr, 1, {"from": accounts[0]})
    assert tx.events["AllocationSet"].values() == [
        accounts[0].address,
        nft_addr,
        1,
        100,
    ]


@enforce_types
def test_max_allocation():
    """Cannot set allocation above max."""
    nft_addr = _rnd_addr()

    with pytest.raises(ValueError) as e:
        veAllocate.setAllocation(10001, nft_addr, 1, {"from": accounts[0]})
    assert "Max Allocation" in str(e)


@enforce_types
def test_getveBatchAllocation():
    """getveAllocation should return the correct allocation."""
    alloc_before = veAllocate.getTotalAllocation(accounts[0])

    nft_addrs = [_rnd_addr() for i in range(2)]

    tx = veAllocate.setBatchAllocation(
        [50, 50], nft_addrs, [1, 1], {"from": accounts[0]}
    )
    assert veAllocate.getveAllocation(accounts[0], nft_addrs[0], 1) == 50

    alloc_after = veAllocate.getTotalAllocation(accounts[0])
    assert alloc_after == alloc_before + 50 + 50


@enforce_types
def test_batch_events():
    """Test emitted events."""
    nft_addrs = [_rnd_addr() for i in range(2)]

    tx = veAllocate.setBatchAllocation(
        [25, 75], nft_addrs, [1, 1], {"from": accounts[0]}
    )
    assert tx.events["AllocationSetMultiple"].values() == [
        accounts[0].address,
        nft_addrs,
        [1, 1],
        [25, 75],
    ]


@enforce_types
def test_batch_max_allocation():
    """Cannot set allocation above max."""
    nft_addrs = [_rnd_addr() for i in range(2)]

    with pytest.raises(ValueError) as e:
        veAllocate.setBatchAllocation(
            [3500, 7500], nft_addrs, [1, 1], {"from": accounts[0]}
        )
    assert "Max Allocation" in str(e)


@enforce_types
def test_batch_reverts():
    """Cannot have different lengths in arrays."""
    two_addrs = [_rnd_addr() for i in range(2)]
    three_addrs = two_addrs + [_rnd_addr()]

    with pytest.raises(ValueError) as e:
        veAllocate.setBatchAllocation(
            [3500, 7500], three_addrs, [1, 1], {"from": accounts[0]}
        )
    assert "Nft array size missmatch" in str(e)

    with pytest.raises(ValueError) as e:
        veAllocate.setBatchAllocation(
            [3500, 7500], two_addrs, [1], {"from": accounts[0]}
        )
    assert "Chain array size missmatch" in str(e)


@enforce_types
def _rnd_addr() -> str:
    base_s = "0x0000000000000000000000000000000000"  # 6 chars short
    six_rnd_chars = str(random.randint(0, 1000000)).zfill(6)
    addr = base_s + six_rnd_chars
    return addr


@enforce_types
def setup_function():
    networkutil.connectDev()
    global accounts, veAllocate
    accounts = brownie.network.accounts
    veAllocate = oceanutil.veAllocate()
