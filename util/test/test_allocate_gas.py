import brownie
from enforce_typing import enforce_types
from util.oceanutil import recordDeployedContracts, OCEANtoken
from util.constants import BROWNIE_PROJECT as B
import web3

accounts = brownie.network.accounts
CHAINID = 0
w3 = web3.Web3()

@enforce_types
def batch_allocate(number: int) -> str:
    OCEAN = OCEANtoken()
    df_rewards = B.DFRewards.deploy({"from": accounts[0]})
    addresses = [w3.eth.account.create().address for i in range(number)]
    rewards = [1 for i in range(number)]
    OCEAN.approve(df_rewards,sum(rewards),{"from":accounts[0]})
    tx = df_rewards.allocate(
        addresses,
        rewards,
        OCEAN.address,
        {"from":accounts[0]}
    )
    return tx


@enforce_types
def test_allocate_gas(ADDRESS_FILE, tmp_path):
    recordDeployedContracts(ADDRESS_FILE, CHAINID)

    one = batch_allocate(1)
    two = batch_allocate(2)
    nine = batch_allocate(9)
    ten = batch_allocate(10)
    
    per_iteration1 = two.gas_used - one.gas_used
    per_iteration2 = ten.gas_used - nine.gas_used
    
    assert abs(per_iteration2 - per_iteration1) < 50 # each iteration uses the same amount of gas
    assert abs(per_iteration1 - 23167) < 100 # 23167 is the estimated gas for each iteration
    assert per_iteration1 * 1250 < 30_000_000 # mainnet gas limit

    big_batch = batch_allocate(1250)
    assert big_batch.gas_used < 30_000_000 # should be able to allocate 1250 addresses using less than 30,000,000 gas.
