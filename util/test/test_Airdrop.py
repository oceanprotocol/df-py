import brownie
from enforce_typing import enforce_types

from util.constants import BROWNIE_PROJECT as B
from util.base18 import toBase18, fromBase18
from util import oceanutil

accounts = brownie.network.accounts
a1, a2, a3 = accounts[1].address, accounts[2].address, accounts[3].address


@enforce_types
def test_basic():
    TOK = _deployTOK(accounts[0])
    airdrop = B.DFRewards.deploy({"from": accounts[0]})
    assert airdrop.claimable(a1, TOK.address) == 0


@enforce_types
def test_TOK():
    TOK = _deployTOK(accounts[9])
    TOK.transfer(accounts[0].address, toBase18(100.0), {"from": accounts[9]})

    airdrop = B.DFRewards.deploy({"from": accounts[0]})

    tos = [a1, a2, a3]
    values = [10, 20, 30]
    TOK.approve(airdrop, sum(values), {"from": accounts[0]})
    airdrop.allocate(tos, values, TOK.address, {"from": accounts[0]})

    assert airdrop.claimable(a1, TOK.address) == 10
    assert airdrop.claimable(a2, TOK.address) == 20
    assert airdrop.claimable(a3, TOK.address) == 30

    # a1 claims for itself
    assert TOK.balanceOf(a1) == 0
    airdrop.claim([TOK.address], {"from": accounts[1]})
    assert TOK.balanceOf(a1) == 10

    # a2 claims for itself too
    assert TOK.balanceOf(a2) == 0
    airdrop.claim([TOK.address], {"from": accounts[2]})
    assert TOK.balanceOf(a2) == 20

    # a9 claims for a3
    assert TOK.balanceOf(a3) == 0
    airdrop.claimFor(a3, TOK.address, {"from": accounts[9]})
    assert TOK.balanceOf(a3) == 30


@enforce_types
def test_OCEAN(ADDRESS_FILE):
    oceanutil.recordDeployedContracts(ADDRESS_FILE, "development")
    OCEAN = oceanutil.OCEANtoken()
    assert OCEAN.balanceOf(accounts[0]) >= 10

    airdrop = B.DFRewards.deploy({"from": accounts[0]})

    OCEAN.approve(airdrop, 10, {"from": accounts[0]})
    airdrop.allocate([a1], [10], OCEAN.address, {"from": accounts[0]})

    assert airdrop.claimable(a1, OCEAN.address) == 10

    bal_before = OCEAN.balanceOf(a1)
    airdrop.claim([OCEAN.address], {"from": accounts[1]})
    bal_after = OCEAN.balanceOf(a1)
    assert (bal_after - bal_before) == 10


@enforce_types
def test_multiple_TOK():
    TOK1 = _deployTOK(accounts[0])
    TOK2 = _deployTOK(accounts[0])

    airdrop = B.DFRewards.deploy({"from": accounts[0]})

    tos = [a1, a2, a3]
    values = [10, 20, 30]

    TOK1.approve(airdrop, sum(values), {"from": accounts[0]})
    TOK2.approve(airdrop, sum(values) + 15, {"from": accounts[0]})

    airdrop.allocate(tos, values, TOK1.address, {"from": accounts[0]})
    airdrop.allocate(tos, [x + 5 for x in values], TOK2.address, {"from": accounts[0]})

    assert airdrop.claimables(a1, [TOK1.address, TOK2.address]) == [10, 15]
    assert airdrop.claimables(a2, [TOK1.address, TOK2.address]) == [20, 25]
    assert airdrop.claimables(a3, [TOK1.address, TOK2.address]) == [30, 35]

    # multiple claims

    # a1 claims for itself
    assert TOK1.balanceOf(a1) == 0
    assert TOK2.balanceOf(a1) == 0
    airdrop.claim([TOK1.address, TOK2.address], {"from": accounts[1]})
    assert TOK1.balanceOf(a1) == 10
    assert TOK2.balanceOf(a1) == 15

    # a2 claims for itself
    assert TOK1.balanceOf(a2) == 0
    assert TOK2.balanceOf(a2) == 0
    airdrop.claim([TOK1.address, TOK2.address], {"from": accounts[2]})
    assert TOK1.balanceOf(a2) == 20
    assert TOK2.balanceOf(a2) == 25

    # a3 claims for itself
    assert TOK1.balanceOf(a3) == 0
    assert TOK2.balanceOf(a3) == 0
    airdrop.claim([TOK1.address, TOK2.address], {"from": accounts[3]})
    assert TOK1.balanceOf(a3) == 30
    assert TOK2.balanceOf(a3) == 35

    # a1 can't claim extra
    with brownie.reverts("Nothing to claim"):
        airdrop.claim([TOK1.address, TOK2.address], {"from": accounts[1]})


@enforce_types
def _deployTOK(account):
    return B.Simpletoken.deploy("TOK", "TOK", 18, toBase18(100.0), {"from": account})
