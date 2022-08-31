import brownie
from enforce_typing import enforce_types
from brownie import convert

from util import networkutil, oceanutil
from util.constants import BROWNIE_PROJECT as B
from util.base18 import toBase18

accounts = None
alice = None
bob = None
veOCEAN = None
veDelegation = None
OCEAN = None
WEEK = 7 * 86400
MAXTIME = 4 * 365 * 86400  # 4 years
chain = brownie.network.chain
TA = toBase18(10.0)


@enforce_types
def test_alice_creates_boost():
    """Alice delegates to bob, then we check adjusted balances and delegation."""
    veOCEAN.checkpoint()
    OCEAN.approve(veOCEAN.address, TA, {"from": alice})

    t0 = chain.time()
    t1 = t0 // WEEK * WEEK
    t2 = t1 + WEEK * 5
    chain.sleep(t1 - t0)

    assert OCEAN.balanceOf(alice) != 0
    veOCEAN.create_lock(TA, t2, {"from": alice})
    assert OCEAN.balanceOf(alice) == 0

    token_id = convert.to_uint(alice.address) << 96

    veDelegation.create_boost(
        alice,
        bob,
        10_000,
        0,
        veOCEAN.locked__end(alice),
        0,
        {"from": alice},
    )  # 10_000 is max percentage

    with brownie.multicall(block_identifier=chain.height):
        alice_adj_balance = veDelegation.adjusted_balance_of(alice)
        bob_adj_balance = veDelegation.adjusted_balance_of(bob)

        alice_delegated_boost = veDelegation.delegated_boost(alice)
        bob_received_boost = veDelegation.received_boost(bob)

        alice_veOCEAN_balance = veOCEAN.balanceOf(alice)
        token_boost_value = veDelegation.token_boost(token_id)

    assert alice_adj_balance == 0
    assert bob_adj_balance == alice_veOCEAN_balance
    assert bob_received_boost == alice_delegated_boost
    assert token_boost_value == alice_delegated_boost
    assert veDelegation.token_expiry(token_id) == (t2 // WEEK) * WEEK


@enforce_types
def setup_function():
    global accounts, alice, bob, veOCEAN, OCEAN, veDelegation
    networkutil.connect(networkutil.DEV_CHAINID)
    oceanutil.recordDevDeployedContracts()
    accounts = brownie.network.accounts

    alice = accounts.add()
    bob = accounts.add()

    OCEAN = oceanutil.OCEANtoken()
    veOCEAN = B.veOcean.deploy(
        OCEAN.address, "veOCEAN", "veOCEAN", "0.1.0", {"from": alice}
    )

    veDelegation = B.veDelegation.deploy(
        "Voting Escrow Boost Delegation",
        "veDelegation",
        "",
        veOCEAN.address,
        {"from": alice},
    )

    OCEAN.transfer(alice, TA, {"from": accounts[0]})
    OCEAN.transfer(bob, TA, {"from": accounts[0]})
