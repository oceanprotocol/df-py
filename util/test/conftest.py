import brownie
from enforce_typing import enforce_types
import os
import pytest
import random

from util import chainlist, constants, graphutil, oceanutil
from util.base18 import toBase18, fromBase18

brownie.network.connect("development")  #ie ganache / barge, CHAINID = 0

accounts = brownie.network.accounts

# pool constants
NUM_STAKERS_PER_POOL = 2  # 3
NUM_CONSUMES = 3  # 100

AMT_OCEAN_PER_ACCOUNT = 100000.0
AVG_INIT_OCEAN_STAKE = 100.0
AVG_DT_OCEAN_RATE = 1.0
AVG_OCEAN_STAKE = 10.0
MAX_OCEAN_IN_BUY = 10000.0
MIN_POOL_BPTS_OUT_FROM_STAKE = 0.1


@pytest.fixture
@enforce_types
def ADDRESS_FILE() -> str:
    return chainlist.chainIdToAddressFile(chainID=0)


@enforce_types
def fillAccountsWithOCEAN():
    OCEAN = oceanutil.OCEANtoken()

    for i in range(1, 10):
        bal_before: int = fromBase18(OCEAN.balanceOf(accounts[i]))
        if bal_before < 1000:
            OCEAN.transfer(accounts[i], toBase18(1000.0), {"from": accounts[0]})
        bal_after: int = fromBase18(OCEAN.balanceOf(accounts[i]))
        print(f"Account #{i} has {bal_after} OCEAN")
    print(f"Account #0 has {fromBase18(OCEAN.balanceOf(accounts[0]))} OCEAN")


@enforce_types
def randomDeployTokensAndPoolsThenConsume(num_pools: int):
    # create random NUM_POOLS. Randomly add stake.
    tups = []  # (pub_account_i, DT, pool)
    for pool_i in range(num_pools):
        if pool_i < len(accounts):
            account_i = pool_i
        else:
            account_i = random.randint(len(accounts))
        (DT, pool) = randomDeployPool(accounts[account_i])
        randomAddStake(pool, account_i)
        tups.append((account_i, DT, pool))

    # consume data assets randomly
    for consume_i in range(NUM_CONSUMES):
        tup = random.choice(tups)
        (pub_account_i, DT, pool) = tup

        # choose consume account
        cand_I = [i for i in range(10) if i != pub_account_i]
        consume_i = random.choice(cand_I)
        consume_account = accounts[consume_i]

        # buy asset
        DT_buy_amt = 1.0
        buyDT(pool, DT, DT_buy_amt, MAX_OCEAN_IN_BUY, consume_account)

        # consume asset
        pub_account = accounts[pub_account_i]
        consumeDT(DT, pub_account, consume_account)

    return tups


@enforce_types
def consumeDT(DT, pub_account, consume_account):
    service_index = 0
    provider_fee = oceanutil.get_zero_provider_fee_tuple(pub_account)
    consume_mkt_fee = oceanutil.get_zero_consume_mkt_fee_tuple()
    DT.startOrder(
        consume_account,
        service_index,
        provider_fee,
        consume_mkt_fee,
        {"from": consume_account},
    )


@enforce_types
def randomAddStake(pool, pub_account_i: int):
    cand_account_I = [i for i in range(10) if i != pub_account_i]
    account_I = random.sample(cand_account_I, NUM_STAKERS_PER_POOL)
    for account_i in account_I:
        OCEAN_stake = AVG_OCEAN_STAKE * (1 + 0.1 * random.random())
        addStake(pool, OCEAN_stake, accounts[account_i])


@enforce_types
def addStake(pool, OCEAN_stake: float, from_account):
    OCEAN = oceanutil.OCEANtoken()
    OCEAN.approve(pool.address, toBase18(OCEAN_stake), {"from": from_account})

    token_amt_in = toBase18(OCEAN_stake)
    min_pool_amt_out = toBase18(MIN_POOL_BPTS_OUT_FROM_STAKE)  # magic number

    # assert tokenAmountIn <= poolBalanceOfToken * MAX_IN_RATIO, "ERR_MAX_IN_RATIO
    pool.joinswapExternAmountIn(token_amt_in, min_pool_amt_out, {"from": from_account})


@enforce_types
def buyDT(pool, DT, DT_buy_amt: float, max_OCEAN: float, from_account):
    OCEAN = oceanutil.OCEANtoken()
    OCEAN.approve(pool.address, toBase18(max_OCEAN), {"from": from_account})

    tokenInOutMarket = [
        OCEAN.address,  # token in address
        DT.address,  # token out address
        constants.ZERO_ADDRESS,  # market fee  address
    ]
    amountsInOutMaxFee = [
        toBase18(max_OCEAN),  # max OCEAN in
        toBase18(DT_buy_amt),  # target DT out
        toBase18(AVG_DT_OCEAN_RATE * 10),  # max price
        0,  # swap market fee
    ]

    # the following test will pass until lotsa activity
    spot_price = fromBase18(pool.getSpotPrice(OCEAN.address, DT.address, 0))
    assert AVG_DT_OCEAN_RATE / 5 <= spot_price <= AVG_DT_OCEAN_RATE * 5

    # spotPriceBefore = calcSpotPrice(..)
    # assert spotPriceBefore <= (max price)], "ERR_BAD_LIMIT_PRICE"
    pool.swapExactAmountOut(
        tokenInOutMarket, amountsInOutMaxFee, {"from": from_account}
    )


@enforce_types
def randomDeployPool(pub_account):
    init_OCEAN_stake = AVG_INIT_OCEAN_STAKE * (1 + 0.1 * random.random())
    DT_OCEAN_rate = AVG_DT_OCEAN_RATE * (1 + 0.1 * random.random())
    return deployPool(init_OCEAN_stake, DT_OCEAN_rate, pub_account)


@enforce_types
def deployPool(init_OCEAN_stake: float, DT_OCEAN_rate: float, from_account):
    data_NFT = oceanutil.createDataNFT("1", "1", from_account)
    DT = oceanutil.createDatatokenFromDataNFT("1", "1", data_NFT, from_account)

    pool = oceanutil.createBPoolFromDatatoken(
        DT,
        from_account,
        init_OCEAN_liquidity=init_OCEAN_stake,
        DT_OCEAN_rate=DT_OCEAN_rate,
    )

    return (DT, pool)
