import random
import brownie

from enforce_typing import enforce_types
from util import constants, oceanutil
from util.base18 import toBase18, fromBase18

network = brownie.network

# pool constants
NUM_STAKERS_PER_POOL = 2  # 3
NUM_CONSUMES = 3  # 100

# ve constants
NUM_LOCKS = 3
LOCK_AMOUNT = toBase18(1.0)
WEEK = 7 * 86400
MAXTIME = 4 * 365 * 86400  # 4 years
NUM_ALLOCATES = 3

AMT_OCEAN_PER_ACCOUNT = 100000.0

AVG_INIT_TOKEN_STAKE = 100.0
AVG_DT_TOKEN_RATE = 1.0
AVG_TOKEN_STAKE = 10.0
MAX_TOKEN_IN_BUY = 10000.0  # e.g. max OCEAN
MIN_POOL_BPTS_OUT_FROM_STAKE = 0.1


@enforce_types
def fillAccountsWithToken(token):
    accounts = network.accounts
    for i in range(1, 10):
        bal_before: int = fromBase18(token.balanceOf(accounts[i]))
        if bal_before < 1000:
            token.transfer(accounts[i], toBase18(1000.0), {"from": accounts[0]})
        # bal_after: int = fromBase18(token.balanceOf(accounts[i]))

    print(f"fillAccountsWithToken({token.symbol()}), balances after:")
    for i in range(10):
        amt = fromBase18(token.balanceOf(accounts[i]))
        print(f"  Account #{i} has {amt} {token.symbol()}")


@enforce_types
def fillAccountsWithOCEAN():
    OCEAN = oceanutil.OCEANtoken()
    fillAccountsWithToken(OCEAN)


@enforce_types
def randomDeployTokensAndPoolsThenConsume(num_pools: int, base_token):
    accounts = network.accounts

    # create random NUM_POOLS. Randomly add stake.
    tups = []  # (pub_account_i, DT, pool)
    for pool_i in range(num_pools):
        if pool_i < len(accounts):
            account_i = pool_i
        else:
            account_i = random.randint(0, len(accounts))
        (DT, pool) = randomDeployPool(accounts[account_i], base_token)
        randomAddStake(pool, account_i, base_token)
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
        buyDT(pool, DT, DT_buy_amt, MAX_TOKEN_IN_BUY, consume_account, base_token)

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
def randomAddStake(pool, pub_account_i: int, token):
    cand_account_I = [i for i in range(10) if i != pub_account_i]
    account_I = random.sample(cand_account_I, NUM_STAKERS_PER_POOL)
    for account_i in account_I:
        TOKEN_stake = AVG_TOKEN_STAKE * (1 + 0.1 * random.random())
        addStake(pool, TOKEN_stake, network.accounts[account_i], token)


@enforce_types
def addStake(pool, TOKEN_stake: float, from_account, token):
    token.approve(pool.address, toBase18(TOKEN_stake), {"from": from_account})

    token_amt_in = toBase18(TOKEN_stake)
    min_pool_amt_out = toBase18(MIN_POOL_BPTS_OUT_FROM_STAKE)  # magic number

    # assert tokenAmountIn <= poolBalanceOfToken * MAX_IN_RATIO, "ERR_MAX_IN_RATIO
    pool.joinswapExternAmountIn(token_amt_in, min_pool_amt_out, {"from": from_account})


@enforce_types
def buyDT(pool, DT, DT_buy_amt: float, max_TOKEN: float, from_account, base_token):
    base_token.approve(pool.address, toBase18(max_TOKEN), {"from": from_account})

    tokenInOutMarket = [
        base_token.address,  # token in address
        DT.address,  # token out address
        constants.ZERO_ADDRESS,  # market fee  address
    ]
    amountsInOutMaxFee = [
        toBase18(max_TOKEN),  # max TOKEN in
        toBase18(DT_buy_amt),  # target DT out
        toBase18(AVG_DT_TOKEN_RATE * 10),  # max price
        0,  # swap market fee
    ]

    # the following test will pass until lotsa activity
    spot_price = fromBase18(pool.getSpotPrice(base_token.address, DT.address, 0))
    assert AVG_DT_TOKEN_RATE / 5 <= spot_price <= AVG_DT_TOKEN_RATE * 5

    # spotPriceBefore = calcSpotPrice(..)
    # assert spotPriceBefore <= (max price)], "ERR_BAD_LIMIT_PRICE"
    pool.swapExactAmountOut(
        tokenInOutMarket, amountsInOutMaxFee, {"from": from_account}
    )


@enforce_types
def randomDeployPool(pub_account, token):
    init_TOKEN_stake = AVG_INIT_TOKEN_STAKE * (1 + 0.1 * random.random())
    DT_TOKEN_rate = AVG_DT_TOKEN_RATE * (1 + 0.1 * random.random())
    return deployPool(init_TOKEN_stake, DT_TOKEN_rate, pub_account, token)


@enforce_types
def deployPool(init_TOKEN_stake: float, DT_TOKEN_rate: float, from_account, token):
    data_NFT = oceanutil.createDataNFT("1", "1", from_account)
    DT = oceanutil.createDatatokenFromDataNFT("1", "1", data_NFT, from_account)

    pool = oceanutil.createBPoolFromDatatoken(
        DT,
        token,
        from_account,
        init_TOKEN_liquidity=init_TOKEN_stake,
        DT_TOKEN_rate=DT_TOKEN_rate,
    )

    return (DT, pool)


@enforce_types
def randomCreateDataNFTWithFREs(num_FRE: int, base_token, accounts):
    # create random num_FRE.
    tups = []  # (pub_account_i, data_NFT, DT, FRE)
    for FRE_i in range(num_FRE):
        if FRE_i < len(accounts):
            account_i = FRE_i
        else:
            account_i = random.randint(0, len(accounts))
        (data_NFT, DT, exchangeId) = oceanutil.createDataNFTWithFRE(
            accounts[account_i], base_token
        )
        assert oceanutil.FixedPrice().isActive(exchangeId) is True
        tups.append((account_i, data_NFT, DT, exchangeId))

    return tups


@enforce_types
def buyDTFRE(exchangeId, DT_buy_amt: float, max_TOKEN: float, from_account, base_token):
    base_token.approve(
        oceanutil.FixedPrice().address, toBase18(max_TOKEN), {"from": from_account}
    )

    feesInfo = oceanutil.FixedPrice().getFeesInfo(exchangeId)
    assert base_token.balanceOf(from_account) >= toBase18(max_TOKEN)
    oceanutil.FixedPrice().buyDT(
        exchangeId,
        toBase18(DT_buy_amt),
        toBase18(max_TOKEN),
        feesInfo[1],
        feesInfo[0],
        {"from": from_account},
    )


@enforce_types
def randomConsumeFREs(FRE_tup: list, base_token):
    accounts = network.accounts

    # consume data assets from FREs randomly
    for consume_i in range(NUM_CONSUMES):
        tup = random.choice(FRE_tup)
        (pub_account_i, _, DT, exchangeId) = tup

        # choose consume account
        cand_I = [i for i in range(10) if i != pub_account_i]
        consume_i = random.choice(cand_I)
        consume_account = accounts[consume_i]

        # buy asset
        DT_buy_amt = 1.0
        buyDTFRE(exchangeId, DT_buy_amt, MAX_TOKEN_IN_BUY, consume_account, base_token)

        # consume asset
        pub_account = accounts[pub_account_i]
        consumeDT(DT, pub_account, consume_account)


@enforce_types
def randomLockAndAllocate():
    accounts = network.accounts
    OCEAN = oceanutil.OCEANtoken()
    pub_account_i = accounts[0]

    t0 = network.chain.time()
    t1 = t0 // WEEK * WEEK + WEEK  # what's going on here? I need to break this down.
    t2 = t1 + WEEK
    network.chain.sleep(t1 - t0)

    # Lock randomly
    for _ in range(NUM_LOCKS):
        # choose lock account
        cand_I = [i for i in range(10) if i != pub_account_i]
        lock_account_i = random.choice(cand_I)
        lock_account = accounts[lock_account_i]

        # Approve locking OCEAN
        assert OCEAN.balanceOf(lock_account) != 0
        OCEAN.approve(oceanutil.veOCEAN().address, LOCK_AMOUNT, {"from": lock_account})

        # Create lock
        oceanutil.veOCEAN().withdraw({"from": lock_account})
        oceanutil.veOCEAN().create_lock(LOCK_AMOUNT, t2, {"from": lock_account})

        oceanutil.set_allocation(
            1.0,
            lock_account,
            8996,
            lock_account,
        )
