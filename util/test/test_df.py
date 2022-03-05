import brownie
import random

from util.base18 import toBase18, fromBase18
from util.constants import BROWNIE_PROJECT
from util.globaltokens import fundOCEANFromAbove, OCEANtoken
from util import oceanv4util

accounts = brownie.network.accounts

def test1():
    brownie.chain.reset()
    OCEAN = OCEANtoken()

    #fund 10 accounts
    for i in range(10):
        fundOCEANFromAbove(accounts[i].address, toBase18(10000))

    #first 3 accounts create a random pool. Randomly add stake.
    for account_i in range(3):
        (DT, pool, ssbot) = _randomDeployPool(accounts[account_i])
        _randomAddStake(pool, account_i)

def _randomAddStake(pool, pub_account_i):
    cand_account_I = [i for i in range(10) if i != pub_account_i]
    account_I = random.sample(cand_account_I, 3)
    for account_i in account_I:
        OCEAN_stake = 100 + random.random() * 900
        _addStake(pool, OCEAN_stake, accounts[account_i])

def _addStake(pool, OCEAN_stake, from_account):
    OCEAN = OCEANtoken()
    OCEAN.approve(pool.address, toBase18(OCEAN_stake), {"from": from_account})
    pool.joinswapExternAmountIn(
        toBase18(OCEAN_stake), toBase18(0.1),  {"from": from_account})
    
def _randomDeployPool(pub_account):
    init_OCEAN_stake = 100 + random.random() * 1000
    DT_OCEAN_rate = 0.1 + random.random() * 0.1
    DT_cap = int(1000 + random.random() * 10000)
    return _deployPool(
        init_OCEAN_stake, DT_OCEAN_rate, DT_cap, pub_account)

def _deployPool(init_OCEAN_stake, DT_OCEAN_rate, DT_cap, from_account):
    router = oceanv4util.deployRouter(from_account)

    (data_NFT, erc721_factory) = oceanv4util.createDataNFT(
        "dataNFT", "DATANFTSYMBOL", from_account, router)

    DT = oceanv4util.createDatatokenFromDataNFT(
        "DT", "DTSYMBOL", DT_cap, data_NFT, from_account)

    pool = oceanv4util.createBPoolFromDatatoken(
        DT,
        erc721_factory,
        from_account,
        init_OCEAN_stake,
        DT_OCEAN_rate,
        DT_vest_amt=0,
    )

    ssbot_address = pool.getController()
    ssbot = BROWNIE_PROJECT.SideStaking.at(ssbot_address)

    return (DT, pool, ssbot)
