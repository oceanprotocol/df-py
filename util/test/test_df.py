import brownie
import random

from util.base18 import toBase18, fromBase18
from util.constants import BROWNIE_PROJECT, ZERO_ADDRESS
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
    tups = [] # (pub_account_i, DT, pool, ssbot)
    for account_i in range(3):
        (DT, pool, ssbot) = _randomDeployPool(accounts[account_i])
        _randomAddStake(pool, account_i)
        tups.append((account_i, DT, pool, ssbot))

    #consume data assets randomly
    num_consumes = 7 #100
    for consume_i in range(num_consumes):
        tup = random.choice(tups)
        (pub_account_i, DT, pool, ssbot) = tup

        #choose consume account
        cand_I = [i for i in range(10) if i != pub_account_i]
        consume_i = random.choice(cand_I)
        consume_account = accounts[consume_i]

        #buy asset
        DT_buy_amt = 1.0
        max_OCEAN = 10000.0
        _buyDT(pool, DT, DT_buy_amt, max_OCEAN, consume_account)

        #consume asset
        #FIXME

def _randomAddStake(pool, pub_account_i):
    cand_account_I = [i for i in range(10) if i != pub_account_i]
    account_I = random.sample(cand_account_I, 3)
    for account_i in account_I:
        OCEAN_stake = 100 + random.random() * 100
        _addStake(pool, OCEAN_stake, accounts[account_i])

def _addStake(pool, OCEAN_stake, from_account):
    OCEAN = OCEANtoken()
    OCEAN.approve(pool.address, toBase18(OCEAN_stake), {"from": from_account})
    
    token_amt_in = toBase18(OCEAN_stake)
    min_pool_amt_out = toBase18(0.1) #magic number
    pool.joinswapExternAmountIn(
        token_amt_in, min_pool_amt_out,  {"from": from_account})

def _buyDT(pool, DT, DT_buy_amt: float, max_OCEAN, from_account):
    OCEAN = OCEANtoken()
    OCEAN.approve(pool.address, toBase18(max_OCEAN), {"from": from_account})

    tokenInOutMarket = [
        OCEAN.address, # token in address
        DT.address,    # token out address
        ZERO_ADDRESS,  # market fee  address
    ]
    amountsInOutMaxFee = [
        toBase18(max_OCEAN),  # max OCEAN in
        toBase18(DT_buy_amt), # target DT out
        2 * 255,              # max price
        0,                    # swap market fee
    ]
    pool.swapExactAmountOut(
        tokenInOutMarket, amountsInOutMaxFee, {"from": from_account})
    
def _randomDeployPool(pub_account):
    init_OCEAN_stake = 1000 + random.random() * 1000
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
