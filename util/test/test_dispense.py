import brownie
from enforce_typing import enforce_types
import os
import pytest

from util import dispense
from util.oceanutil import recordDeployedContracts, OCEANtoken
from util.base18 import fromBase18, toBase18
from util.constants import BROWNIE_PROJECT as B

accounts = brownie.network.accounts
a1, a2, a3 = accounts[1].address, accounts[2].address, accounts[3].address


@enforce_types
def test_small_batch(ADDRESS_FILE, tmp_path):
    recordDeployedContracts(ADDRESS_FILE, "development")
    OCEAN = OCEANtoken()
    airdrop = B.Airdrop.deploy({"from": accounts[0]})

    rewards_at_chain = {a1: 0.1, a2: 0.2, a3: 0.3}
    dispense.dispense(
        rewards_at_chain,
        airdrop_addr = airdrop.address,
        token_address = OCEAN.address,
        from_account = accounts[0],
    )

    # a1 claims for itself
    bal_before = fromBase18(OCEAN.balanceOf(a1))
    airdrop.claim([OCEAN.address], {"from": accounts[1]})
    bal_after = fromBase18(OCEAN.balanceOf(a1))
    assert (bal_after - bal_before) == pytest.approx(0.1)

    # a9 claims on behalf of a1
    bal_before = fromBase18(OCEAN.balanceOf(a3))
    airdrop.claimFor(a3, OCEAN.address, {"from": accounts[9]})
    bal_after = fromBase18(OCEAN.balanceOf(a3))
    assert (bal_after - bal_before) == pytest.approx(0.3)


@enforce_types
def test_batching(ADDRESS_FILE):
    recordDeployedContracts(ADDRESS_FILE, "development")
    OCEAN = OCEANtoken()
    airdrop = B.Airdrop.deploy({"from": accounts[0]})

    batch_size = 3
    N = batch_size * 3 + 1  # enough accounts to ensure batching
    assert len(accounts) >= N

    rewards = {accounts[i]: (i + 1.0) for i in range(N)}

    dispense.dispense(
        rewards_at_chain,
        airdrop_addr = airdrop.address,
        token_address = OCEAN.address,
        from_account = accounts[0],
        batch_size = batch_size
    )
