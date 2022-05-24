import brownie
from enforce_typing import enforce_types

from util.constants import BROWNIE_PROJECT as B
from util.base18 import toBase18
from util import oceanutil

accounts = brownie.network.accounts
a1, a2, a3 = accounts[1].address, accounts[2].address, accounts[3].address

CHAINID = 0


@enforce_types
def test_basic():
    TOK = _deployTOK(accounts[0])
    df_rewards = B.DFRewards.deploy({"from": accounts[0]})
    assert df_rewards.claimable(a1, TOK.address) == 0


@enforce_types
def test_lostERC20():
    # Can recover when an account accidentally sends ERC20 to DFRewards.sol?
    # test_withdrawfunc.py handles this, so no work here
    pass


@enforce_types
def test_lostETH():
    # Can recover when an account accidentally sends ETH to DFRewards.sol?
    # test_withdrawfunc.py handles this, so no work here
    pass


@enforce_types
def test_TOK():
    TOK = _deployTOK(accounts[9])
    TOK.transfer(accounts[0].address, toBase18(100.0), {"from": accounts[9]})

    df_rewards = B.DFRewards.deploy({"from": accounts[0]})

    tos = [a1, a2, a3]
    values = [10, 20, 30]
    TOK.approve(df_rewards, sum(values), {"from": accounts[0]})
    df_rewards.allocate(tos, values, TOK.address, {"from": accounts[0]})

    assert df_rewards.claimable(a1, TOK.address) == 10
    assert df_rewards.claimable(a2, TOK.address) == 20
    assert df_rewards.claimable(a3, TOK.address) == 30

    # a1 claims for itself
    assert TOK.balanceOf(a1) == 0
    df_rewards.claim([TOK.address], {"from": accounts[1]})
    assert TOK.balanceOf(a1) == 10

    # a2 claims for itself too
    assert TOK.balanceOf(a2) == 0
    df_rewards.claim([TOK.address], {"from": accounts[2]})
    assert TOK.balanceOf(a2) == 20

    # a9 claims for a3
    assert TOK.balanceOf(a3) == 0
    df_rewards.claimFor(a3, TOK.address, {"from": accounts[9]})
    assert TOK.balanceOf(a3) == 30


@enforce_types
def test_OCEAN(ADDRESS_FILE):
    oceanutil.recordDeployedContracts(ADDRESS_FILE, CHAINID)
    OCEAN = oceanutil.OCEANtoken()
    assert OCEAN.balanceOf(accounts[0]) >= 10

    df_rewards = B.DFRewards.deploy({"from": accounts[0]})

    OCEAN.approve(df_rewards, 10, {"from": accounts[0]})
    df_rewards.allocate([a1], [10], OCEAN.address, {"from": accounts[0]})

    assert df_rewards.claimable(a1, OCEAN.address) == 10

    bal_before = OCEAN.balanceOf(a1)
    df_rewards.claim([OCEAN.address], {"from": accounts[1]})
    bal_after = OCEAN.balanceOf(a1)
    assert (bal_after - bal_before) == 10


@enforce_types
def test_multiple_TOK():
    TOK1 = _deployTOK(accounts[0])
    TOK2 = _deployTOK(accounts[0])

    df_rewards = B.DFRewards.deploy({"from": accounts[0]})

    tos = [a1, a2, a3]
    values = [10, 20, 30]

    TOK1.approve(df_rewards, sum(values), {"from": accounts[0]})
    TOK2.approve(df_rewards, sum(values) + 15, {"from": accounts[0]})

    df_rewards.allocate(tos, values, TOK1.address, {"from": accounts[0]})
    df_rewards.allocate(
        tos, [x + 5 for x in values], TOK2.address, {"from": accounts[0]}
    )

    assert df_rewards.claimables(a1, [TOK1.address, TOK2.address]) == [10, 15]
    assert df_rewards.claimables(a2, [TOK1.address, TOK2.address]) == [20, 25]
    assert df_rewards.claimables(a3, [TOK1.address, TOK2.address]) == [30, 35]

    # multiple claims

    # a1 claims for itself
    assert TOK1.balanceOf(a1) == 0
    assert TOK2.balanceOf(a1) == 0
    df_rewards.claim([TOK1.address, TOK2.address], {"from": accounts[1]})
    assert TOK1.balanceOf(a1) == 10
    assert TOK2.balanceOf(a1) == 15

    # a2 claims for itself
    assert TOK1.balanceOf(a2) == 0
    assert TOK2.balanceOf(a2) == 0
    df_rewards.claim([TOK1.address, TOK2.address], {"from": accounts[2]})
    assert TOK1.balanceOf(a2) == 20
    assert TOK2.balanceOf(a2) == 25

    # a3 claims for itself
    assert TOK1.balanceOf(a3) == 0
    assert TOK2.balanceOf(a3) == 0
    df_rewards.claim([TOK1.address, TOK2.address], {"from": accounts[3]})
    assert TOK1.balanceOf(a3) == 30
    assert TOK2.balanceOf(a3) == 35

    # a1 can't claim extra
    with brownie.reverts("Nothing to claim"):
        df_rewards.claim([TOK1.address, TOK2.address], {"from": accounts[1]})


@enforce_types
def _deployTOK(account):
    return B.Simpletoken.deploy("TOK", "TOK", 18, toBase18(100.0), {"from": account})
