import pytest
from enforce_typing import enforce_types
from web3.exceptions import ContractLogicError  # pylint: disable=no-name-in-module
from web3.logs import DISCARD  # pylint: disable=no-name-in-module

from df_py.web3util.contract_base import ContractBase
from df_py.web3util.networkutil import chain_id_to_web3
from df_py.web3util.oceantestutil import get_account0

veAllocate = None


@enforce_types
def test_getveAllocation(all_accounts):
    """getveAllocation should return the correct allocation."""
    accounts = all_accounts
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
def test_events(all_accounts):
    """Test emitted events."""
    accounts = all_accounts
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
def test_max_allocation(all_accounts):
    """Cannot set allocation above max."""
    accounts = all_accounts
    nftaddr = accounts[1].address

    with pytest.raises(ContractLogicError, match="Max Allocation"):
        veAllocate.setAllocation(10001, nftaddr, 1, {"from": accounts[0]})


@enforce_types
def test_getveBatchAllocation(all_accounts):
    """getveAllocation should return the correct allocation."""
    accounts = all_accounts
    nftaddr1 = accounts[0].address
    nftaddr2 = accounts[1].address

    _ = veAllocate.setBatchAllocation(
        [50, 50], [nftaddr1, nftaddr2], [1, 1], {"from": accounts[0]}
    )
    assert veAllocate.getveAllocation(accounts[0], nftaddr1, 1) == 50
    assert veAllocate.getTotalAllocation(accounts[0]) == 100


@enforce_types
def test_batch_events(all_accounts):
    """Test emitted events."""
    accounts = all_accounts
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
def test_batch_max_allocation(all_accounts):
    """Cannot set allocation above max."""
    accounts = all_accounts
    nftaddr1 = accounts[1].address
    nftaddr2 = accounts[2].address
    with pytest.raises(ContractLogicError, match="Max Allocation"):
        veAllocate.setBatchAllocation(
            [3500, 7500], [nftaddr1, nftaddr2], [1, 1], {"from": accounts[0]}
        )


@enforce_types
def test_batch_reverts(all_accounts):
    """Cannot have different lengths in arrays."""
    accounts = all_accounts
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
    w3 = chain_id_to_web3(8996)
    w3.eth.default_account = get_account0().address
    veAllocate = ContractBase(w3, "ve/veAllocate", constructor_args=[])
