import brownie
from enforce_typing import enforce_types

from ocean_lib.models.arguments import DataNFTArguments, DatatokenArguments

from util.constants import BROWNIE_PROJECT as B
from util.base18 import toBase18
from util import networkutil, oceanutil


@enforce_types
def test_basic(data_NFT, alice, df_rewards):
    TOK = _deployTOK(data_NFT, alice)
    assert df_rewards.claimable(alice.address, TOK.address) == 0


@enforce_types
def test_TOK(data_NFT, df_rewards, df_strategy):
    TOK = _deployTOK(data_NFT, accounts[9])
    TOK.transfer(acc0, toBase18(100.0), {"from": accounts[9]})

    tos = [a1, a2, a3]
    values = [10, 20, 30]
    TOK.approve(df_rewards, sum(values), {"from": acc0})
    df_rewards.allocate(tos, values, TOK.address, {"from": acc0})

    assert df_rewards.claimable(a1, TOK.address) == 10
    assert df_rewards.claimable(a2, TOK.address) == 20
    assert df_rewards.claimable(a3, TOK.address) == 30

    # a1 claims for itself
    assert TOK.balanceOf(a1) == 0
    df_strategy.claim([TOK.address], {"from": accounts[1]})
    assert TOK.balanceOf(a1) == 10

    # a2 claims for itself too
    assert TOK.balanceOf(a2) == 0
    df_strategy.claim([TOK.address], {"from": accounts[2]})
    assert TOK.balanceOf(a2) == 20

    # a9 claims for a3
    assert TOK.balanceOf(a3) == 0
    df_rewards.claimFor(a3, TOK.address, {"from": accounts[9]})
    assert TOK.balanceOf(a3) == 30


@enforce_types
def test_OCEAN(ocean, df_rewards, df_strategy):
    address_file = networkutil.chainIdToAddressFile(networkutil.DEV_CHAINID)
    oceanutil.recordDeployedContracts(address_file)
    OCEAN = oceanutil.OCEANtoken()
    assert OCEAN.balanceOf(acc0) >= 10

    OCEAN.approve(df_rewards, 10, {"from": acc0})
    df_rewards.allocate([a1], [10], OCEAN.address, {"from": acc0})

    assert df_rewards.claimable(a1, OCEAN.address) == 10

    bal_before = OCEAN.balanceOf(a1)
    df_strategy.claim([OCEAN.address], {"from": accounts[1]})
    bal_after = OCEAN.balanceOf(a1)
    assert (bal_after - bal_before) == 10


@enforce_types
def test_multiple_TOK(ocean, df_rewards, df_strategy):
    data_NFT1 = ocean.data_nft_factory.create(DataNFTArguments('1','1'), acc0)
    data_NFT2 = ocean.data_nft_factory.create(DataNFTArguments('2','2'), acc0)
    
    TOK1 = _deployTOK(data_NFT1, acc0)
    TOK2 = _deployTOK(data_NFT2, acc0)

    tos = [a1, a2, a3]
    values = [10, 20, 30]

    TOK1.approve(df_rewards, sum(values), {"from": acc0})
    TOK2.approve(df_rewards, sum(values) + 15, {"from": acc0})

    df_rewards.allocate(tos, values, TOK1.address, {"from": acc0})
    df_rewards.allocate(
        tos, [x + 5 for x in values], TOK2.address, {"from": acc0}
    )

    assert df_strategy.claimables(a1, [TOK1.address, TOK2.address]) == [10, 15]
    assert df_strategy.claimables(a2, [TOK1.address, TOK2.address]) == [20, 25]
    assert df_strategy.claimables(a3, [TOK1.address, TOK2.address]) == [30, 35]

    # multiple claims

    # a1 claims for itself
    assert TOK1.balanceOf(a1) == 0
    assert TOK2.balanceOf(a1) == 0
    df_strategy.claim([TOK1.address, TOK2.address], {"from": accounts[1]})
    assert TOK1.balanceOf(a1) == 10
    assert TOK2.balanceOf(a1) == 15

    # a2 claims for itself
    assert TOK1.balanceOf(a2) == 0
    assert TOK2.balanceOf(a2) == 0
    df_strategy.claim([TOK1.address, TOK2.address], {"from": accounts[2]})
    assert TOK1.balanceOf(a2) == 20
    assert TOK2.balanceOf(a2) == 25

    # a3 claims for itself
    assert TOK1.balanceOf(a3) == 0
    assert TOK2.balanceOf(a3) == 0
    df_strategy.claim([TOK1.address, TOK2.address], {"from": accounts[3]})
    assert TOK1.balanceOf(a3) == 30
    assert TOK2.balanceOf(a3) == 35

    # a1 can't claim extra
    assert TOK1.balanceOf(a1) == 10
    assert TOK2.balanceOf(a1) == 15
    df_strategy.claim([TOK1.address, TOK2.address], {"from": accounts[1]})
    assert TOK1.balanceOf(a1) == 10
    assert TOK2.balanceOf(a1) == 15


def test_bad_token(ocean, df_rewards):
    badToken = B.Badtoken.deploy(
        "BAD", "BAD", 18, toBase18(10000.0), {"from": acc0}
    )

    tos = [a1, a2, a3]
    values = [10, 20, 30]

    badToken.approve(df_rewards, sum(values), {"from": acc0})

    with brownie.reverts("Not enough tokens"):
        df_rewards.allocate(tos, values, badToken.address, {"from": acc0})


def test_strategies(data_NFT, df_rewards, df_strategy):
    TOK = _deployTOK(data_NFT, acc0)

    # allocate rewards
    tos = [a1, a2, a3]
    values = [10, 20, 30]
    TOK.approve(df_rewards, sum(values), {"from": acc0})
    df_rewards.allocate(tos, values, TOK.address, {"from": acc0})

    assert TOK.balanceOf(df_strategy) == 0
    with brownie.reverts("Caller doesn't match"):
        # tx origin must be a1
        df_strategy.claim(TOK.address, a1, {"from": accounts[2]})

    with brownie.reverts("Caller must be a strategy"):
        # non strategy addresses cannot claim
        df_strategy.claim(TOK.address, a1, {"from": accounts[1]})

    # add strategy
    df_rewards.addStrategy(df_strategy.address)
    assert df_rewards.isStrategy(df_strategy.address)
    assert df_rewards.live_strategies(0) == df_strategy.address

    # should claim since it's a strategy
    df_strategy.claim(TOK.address, a1, {"from": accounts[1]})

    # strategy balance increases
    assert TOK.balanceOf(df_strategy) == 10

    # should claim since it's a strategy
    df_strategy.claim(TOK.address, a2, {"from": accounts[2]})

    # strategy balance increases
    assert TOK.balanceOf(df_strategy) == 30

    # retire strategy
    df_rewards.retireStrategy(df_strategy.address)
    assert not df_rewards.isStrategy(df_strategy.address)

    with brownie.reverts("Caller must be a strategy"):
        # non strategy addresses cannot claim
        df_strategy.claim(TOK.address, a3, {"from": accounts[3]})

    with brownie.reverts("Ownable: caller is not the owner"):
        # addresses other than the owner cannot add new strategy
        df_rewards.addStrategy(df_strategy.address, {"from": accounts[3]})

    # add strategy
    df_rewards.addStrategy(df_strategy.address)
    assert df_rewards.isStrategy(df_strategy.address)
    assert df_rewards.live_strategies(0) == df_strategy.address

    # should claim since it's a strategy
    df_strategy.claim(TOK.address, a3, {"from": accounts[3]})

    # strategy balance increases
    assert TOK.balanceOf(df_strategy) == 60


@enforce_types
def test_claim_and_restake(ocean, df_rewards, df_strategy):
    address_file = networkutil.chainIdToAddressFile(networkutil.DEV_CHAINID)
    oceanutil.recordDeployedContracts(address_file)
    OCEAN = oceanutil.OCEANtoken()
    deployer = acc0
    bob = accounts[1]

    OCEAN.transfer(bob, 100, {"from": deployer})

    df_rewards.addStrategy(df_strategy.address)

    veOCEAN = B.veOcean.deploy(
        OCEAN.address, "veOCEAN", "veOCEAN", "0.1.0", {"from": deployer}
    )

    OCEAN.approve(veOCEAN.address, 100, {"from": bob})
    unlock_time = brownie.network.chain.time() + 14 * 86400
    veOCEAN.create_lock(100, unlock_time, {"from": bob})

    tos = [a1]
    values = [50]
    OCEAN.approve(df_rewards, sum(values), {"from": deployer})
    df_rewards.allocate(tos, values, OCEAN.address, {"from": deployer})

    assert df_rewards.claimable(a1, OCEAN.address) == 50

    with brownie.reverts("Not enough rewards"):
        # Cannot claim what you don't have
        df_strategy.claimAndStake(
            OCEAN,
            100,
            veOCEAN,
            {"from": bob},
        )

    # veBalBefore = veOCEAN.balanceOf(deployer)
    df_strategy.claimAndStake(
        OCEAN,
        50,
        veOCEAN,
        {"from": bob},
    )

    assert df_rewards.claimable(a1, OCEAN.address) == 0


@enforce_types
def _deployTOK(data_NFT, account):
    assert account is not None
    cap = toBase18(100.0)
    args = DatatokenArguments('TOK','TOK',cap=toBase18(100.0))
    TOK = data_NFT.create_datatoken(args, account)
    return TOK
