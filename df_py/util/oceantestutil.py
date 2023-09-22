import random

from enforce_typing import enforce_types

from df_py.util import constants, oceanutil
from df_py.util.base18 import from_wei, to_wei

# pool constants
NUM_STAKERS_PER_POOL = 2  # 3
NUM_CONSUMES = 3  # 100

# ve constants
NUM_LOCKS = 3
LOCK_AMOUNT = to_wei(1000.0)
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
def fill_accounts_with_token(accounts, token):
    for i, account in enumerate(accounts):
        if i == 0:
            continue

        bal_before = from_wei(token.balanceOf(account))
        if bal_before < 1000.0:
            token.transfer(account, to_wei(1000.0), {"from": accounts[0]})

    print(f"fill_accounts_with_token({token.symbol()}), balances after:")
    for account in accounts:
        amt = from_wei(token.balanceOf(account))
        print(f"  Account #{i} has {amt} {token.symbol()}")


@enforce_types
def fill_accounts_with_OCEAN(accounts):
    OCEAN = oceanutil.OCEAN_token()
    fill_accounts_with_token(accounts, OCEAN)


@enforce_types
def consume_DT(DT, pub_account, consume_account):
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
def random_add_stake(pool, pub_account_i: int, token):
    cand_account_I = [i for i in range(10) if i != pub_account_i]
    account_I = random.sample(cand_account_I, NUM_STAKERS_PER_POOL)
    for account_i in account_I:
        TOKEN_stake = AVG_TOKEN_STAKE * (1 + 0.1 * random.random())
        add_stake(pool, TOKEN_stake, network.accounts[account_i], token)


@enforce_types
def add_stake(pool, TOKEN_stake: float, from_account, token):
    token.approve(pool.address, to_wei(TOKEN_stake), {"from": from_account})

    token_amt_in = to_wei(TOKEN_stake)
    min_pool_amt_out = to_wei(MIN_POOL_BPTS_OUT_FROM_STAKE)  # magic number

    # assert tokenAmountIn <= poolBalanceOfToken * MAX_IN_RATIO, "ERR_MAX_IN_RATIO
    pool.joinswapExternAmountIn(token_amt_in, min_pool_amt_out, {"from": from_account})


@enforce_types
def buy_DT(pool, DT, DT_buy_amt: float, max_TOKEN: float, from_account, base_token):
    base_token.approve(pool.address, to_wei(max_TOKEN), {"from": from_account})

    tokenInOutMarket = [
        base_token.address,  # token in address
        DT.address,  # token out address
        constants.ZERO_ADDRESS,  # market fee  address
    ]
    amountsInOutMaxFee = [
        to_wei(max_TOKEN),  # max TOKEN in
        to_wei(DT_buy_amt),  # target DT out
        to_wei(AVG_DT_TOKEN_RATE * 10),  # max price
        0,  # swap market fee
    ]

    # the following test will pass until lotsa activity
    spot_price = from_wei(pool.getSpotPrice(base_token.address, DT.address, 0))
    assert AVG_DT_TOKEN_RATE / 5 <= spot_price <= AVG_DT_TOKEN_RATE * 5

    # spotPriceBefore = calcSpotPrice(..)
    # assert spotPriceBefore <= (max price)], "ERR_BAD_LIMIT_PRICE"
    pool.swapExactAmountOut(
        tokenInOutMarket, amountsInOutMaxFee, {"from": from_account}
    )


@enforce_types
def random_create_dataNFT_with_FREs(num_FRE: int, base_token, accounts):
    # create random num_FRE.
    tups = []  # (pub_account_i, data_NFT, DT, FRE)
    for FRE_i in range(num_FRE):
        if FRE_i < len(accounts):
            account_i = FRE_i
        else:
            account_i = random.randint(0, len(accounts))
        (data_NFT, DT, exchangeId) = oceanutil.create_data_nft_with_fre(
            accounts[account_i], base_token
        )
        assert oceanutil.FixedPrice().isActive(exchangeId) is True
        tups.append((account_i, data_NFT, DT, exchangeId))

    return tups


@enforce_types
def buy_DT_FRE(
    exchangeId, DT_buy_amt: float, max_TOKEN: float, from_account, base_token
):
    base_token.approve(
        oceanutil.FixedPrice().address, to_wei(max_TOKEN), {"from": from_account}
    )

    feesInfo = oceanutil.FixedPrice().getFeesInfo(exchangeId)
    oceanutil.FixedPrice().buyDT(
        exchangeId,
        to_wei(DT_buy_amt),
        to_wei(max_TOKEN),
        feesInfo[1],
        feesInfo[0],
        {"from": from_account},
    )


@enforce_types
def random_consume_FREs(FRE_tup: list, base_token):
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
        buy_DT_FRE(
            exchangeId, DT_buy_amt, MAX_TOKEN_IN_BUY, consume_account, base_token
        )

        # consume asset
        pub_account = accounts[pub_account_i]
        consume_DT(DT, pub_account, consume_account)


@enforce_types
def random_lock_and_allocate(tups: list):
    # tups = [(pub_account_i, data_NFT, DT, exchangeId)]

    acc1 = network.accounts[0]
    OCEAN = oceanutil.OCEAN_token()
    veOCEAN = oceanutil.veOCEAN()

    accounts = network.accounts[: len(tups)]

    for account in accounts:
        OCEAN.mint(account, LOCK_AMOUNT, {"from": acc1})

    network.chain.sleep(WEEK * 20)
    t0 = network.chain.time()
    t1 = t0 // WEEK * WEEK + WEEK
    t2 = t1 + WEEK
    network.chain.sleep(t1 - t0)
    network.chain.mine()

    # Lock randomly
    for (i, tup) in enumerate(tups):
        data_nft = tup[1]

        # choose lock account
        lock_account = accounts[i]

        # Approve locking OCEAN
        assert OCEAN.balanceOf(lock_account) != 0
        OCEAN.approve(veOCEAN.address, LOCK_AMOUNT, {"from": lock_account})

        # Check if there is an active lock
        if veOCEAN.balanceOf(lock_account) == 0:
            # Create lock
            veOCEAN.withdraw({"from": lock_account})
            veOCEAN.create_lock(LOCK_AMOUNT, t2, {"from": lock_account})

        assert veOCEAN.balanceOf(lock_account) != 0
        allc_amt = constants.MAX_ALLOCATE - oceanutil.veAllocate().getTotalAllocation(
            lock_account
        )
        oceanutil.set_allocation(
            int(allc_amt),
            data_nft.address,
            8996,
            lock_account,
        )
