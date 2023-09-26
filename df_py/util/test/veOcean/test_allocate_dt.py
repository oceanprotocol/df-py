from enforce_typing import enforce_types
from eth_account import Account
import os
from df_py.util.contract_base import ContractBase
from web3.exceptions import ContractLogicError
import pytest
from web3.logs import DISCARD

from df_py.util.oceanutil import get_rpc_url, get_web3

veAllocate = None

# TODO: unify this accounts thing as a fixture
accounts = [
    Account.from_key(private_key=os.getenv(f"TEST_PRIVATE_KEY{index}"))
    for index in range(0, 9)
]


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

    event = veAllocate.contract.events.AllocationSet().process_receipt(
        tx, errors=DISCARD
    )[0]

    assert event.args.sender == accounts[0].address
    assert event.args.nft == accounts[1].address
    assert event.args.chainId == 1
    assert event.args.amount == 100


@enforce_types
def test_max_allocation():
    """Cannot set allocation above max."""
    nftaddr = accounts[1].address

    with pytest.raises(ContractLogicError, match="Max Allocation"):
        veAllocate.setAllocation(10001, nftaddr, 1, {"from": accounts[0]})


@enforce_types
def test_getveBatchAllocation():
    """getveAllocation should return the correct allocation."""
    nftaddr1 = accounts[0].address
    nftaddr2 = accounts[1].address

    _ = veAllocate.setBatchAllocation(
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
    event = veAllocate.contract.events.AllocationSetMultiple().process_receipt(
        tx, errors=DISCARD
    )[0]

    assert event.args.sender == accounts[0].address
    assert event.args.nft == [nftaddr1, nftaddr2]
    assert event.args.chainId == [1, 1]
    assert event.args.amount == [25, 75]


@enforce_types
def test_batch_max_allocation():
    """Cannot set allocation above max."""
    nftaddr1 = accounts[1].address
    nftaddr2 = accounts[2].address
    with pytest.raises(ContractLogicError, match="Max Allocation"):
        veAllocate.setBatchAllocation(
            [3500, 7500], [nftaddr1, nftaddr2], [1, 1], {"from": accounts[0]}
        )


@enforce_types
def test_batch_reverts():
    """Cannot have different lengths in arrays."""
    nftaddr1 = accounts[1].address
    nftaddr2 = accounts[2].address
    with pytest.raises(ContractLogicError, match="Nft array size missmatch"):
        veAllocate.setBatchAllocation(
            [3500, 7500], [nftaddr1, nftaddr2, nftaddr2], [1, 1], {"from": accounts[0]}
        )
    with pytest.raises(ContractLogicError, match="Chain array size missmatch"):
        veAllocate.setBatchAllocation(
            [3500, 7500], [nftaddr1, nftaddr2], [1], {"from": accounts[0]}
        )


@enforce_types
def setup_function():
    global veAllocate
    w3 = get_web3(get_rpc_url("development"))
    w3.eth.default_account = accounts[0].address
    veAllocate = ContractBase(w3, "ve/veAllocate", constructor_args=[])
