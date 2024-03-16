import os
import random
import time

from enforce_typing import enforce_types
from eth_account import Account
from web3.main import Web3

from df_py.util import constants, networkutil, oceanutil
from df_py.util.base18 import from_wei, to_wei

# pool constants
NUM_STAKERS_PER_POOL = 2  # 3
NUM_CONSUMES = 3  # 100

# ve constants
NUM_LOCKS = 3
LOCK_AMOUNT = to_wei(1000.0)
DAY = 86400
WEEK = 7 * DAY
YEAR = 365 * DAY
MAXTIME = 4 * 365 * 86400  # 4 years
NUM_ALLOCATES = 3

AMT_OCEAN_PER_ACCOUNT = 100000.0

AVG_INIT_TOKEN_STAKE = 100.0
AVG_DT_TOKEN_RATE = 1.0
AVG_TOKEN_STAKE = 10.0
MAX_TOKEN_IN_BUY = 10000.0  # e.g. max OCEAN
MIN_POOL_BPTS_OUT_FROM_STAKE = 0.1


def print_dev_accounts():
    accounts = get_all_accounts()
    print("dev accounts:")
    for i, account in enumerate(accounts):
        print(f"  Account #{i}: {account.address} private key: {account.key.hex()}")


@enforce_types
def fill_accounts_with_token(accounts, token):
    for i, account in enumerate(accounts):
        bal_before = from_wei(token.balanceOf(account))

        if i == 0:
            if bal_before < 10000.0:
                token.mint(account, to_wei(10000.0), {"from": accounts[0]})

            continue

        if bal_before < 1000.0:
            token.transfer(account, to_wei(1000.0), {"from": accounts[0]})

    print(f"fill_accounts_with_token({token.symbol()}), balances after:")
    for i, account in enumerate(accounts):
        amt = from_wei(token.balanceOf(account))
        print(f"  Account #{i} has {amt} {token.symbol()}")


@enforce_types
def fill_accounts_with_OCEAN(accounts):
    OCEAN = oceanutil.OCEAN_token(networkutil.DEV_CHAINID)
    fill_accounts_with_token(accounts, OCEAN)


@enforce_types
def consume_DT(DT, pub_account, consume_account):
    service_index = 0
    w3 = networkutil.chain_id_to_web3(8996)
    account = get_account0()
    w3.eth.default_account = account.address

    provider_fee = oceanutil.get_zero_provider_fee_tuple(w3, pub_account)

    consume_mkt_fee = oceanutil.get_zero_consume_mkt_fee_tuple()
    DT.startOrder(
        consume_account,
        service_index,
        provider_fee,
        consume_mkt_fee,
        {"from": consume_account},
    )

    print(
        f"started order for consume_DT by {consume_account.address} on DT {DT.address}"
    )


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
def random_create_dataNFT_with_FREs(web3: Web3, num_FRE: int, base_token):
    # create random num_FRE.
    accounts = [web3.eth.account.create() for _ in range(num_FRE)]
    for account in accounts:
        networkutil.send_ether(web3, get_account0(), account.address, to_wei(1))
    fill_accounts_with_OCEAN([get_account0()] + accounts)
    tups = []  # (pub_account_i, data_NFT, DT, FRE)
    for FRE_i in range(num_FRE):
        if FRE_i < len(accounts):
            account_i = FRE_i
        else:
            account_i = random.randint(0, len(accounts))

        (data_NFT, DT, exchangeId) = oceanutil.create_data_nft_with_fre(
            web3, accounts[account_i], base_token
        )
        assert oceanutil.FixedPrice(web3.eth.chain_id).isActive(exchangeId) is True
        tups.append((account_i, data_NFT, DT, exchangeId))

    return tups


@enforce_types
def buy_DT_FRE(
    exchangeId, DT_buy_amt: float, max_TOKEN: float, from_account, base_token
):
    chain_id = networkutil.DEV_CHAINID
    base_token.approve(
        oceanutil.FixedPrice(chain_id).address,
        to_wei(max_TOKEN),
        {"from": from_account},
    )

    feesInfo = oceanutil.FixedPrice(chain_id).getFeesInfo(exchangeId)
    oceanutil.FixedPrice(chain_id).buyDT(
        exchangeId,
        to_wei(DT_buy_amt),
        to_wei(max_TOKEN),
        feesInfo[1],
        feesInfo[0],
        {"from": from_account},
    )


@enforce_types
def random_consume_FREs(FRE_tup: list, base_token):
    accounts = get_all_accounts()

    # consume data assets from FREs randomly
    for consume_i in range(NUM_CONSUMES):
        tup = random.choice(FRE_tup)
        (pub_account_i, _, DT, exchangeId) = tup

        # choose consume account
        cand_I = [i for i in range(9) if i != pub_account_i]
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
def random_lock_and_allocate(web3, tups: list):
    acc0 = get_account0()
    OCEAN = oceanutil.OCEAN_token(networkutil.DEV_CHAINID)
    veOCEAN = oceanutil.veOCEAN(networkutil.DEV_CHAINID)

    accounts = get_all_accounts()[: len(tups)]

    for account in accounts:
        OCEAN.mint(account, LOCK_AMOUNT, {"from": acc0})

    provider = web3.provider
    provider.make_request("evm_mine", [])
    provider.make_request("evm_increaseTime", [WEEK * 20])

    t0 = web3.eth.get_block("latest").timestamp
    t1 = t0 // WEEK * WEEK + WEEK
    # solution copied from test_queries, sometimes on ganache the lock
    # doesn't work, so we try again
    t2 = t1 + 4 * YEAR
    provider.make_request("evm_increaseTime", [t1 - t0])
    provider.make_request("evm_mine", [])

    # Lock randomly
    for i, tup in enumerate(tups):
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
            tx = veOCEAN.create_lock(LOCK_AMOUNT, t2, {"from": lock_account})
            receipt = web3.eth.wait_for_transaction_receipt(tx.transactionHash)

            initial_time = time.time()
            while receipt.status == 0:
                time.sleep(1)
                receipt = web3.eth.wait_for_transaction_receipt(tx.transactionHash)
                if time.time() > initial_time + 60:
                    tx = veOCEAN.create_lock(LOCK_AMOUNT, t2, {"from": lock_account})
                    assert tx.status == 1
                    break

        print(f"locked {LOCK_AMOUNT} for: Account #{i} of {len(tups)}")
        assert veOCEAN.balanceOf(lock_account) != 0
        allc_amt = constants.MAX_ALLOCATE - oceanutil.veAllocate(
            networkutil.DEV_CHAINID
        ).getTotalAllocation(lock_account)
        oceanutil.set_allocation(
            int(allc_amt),
            data_nft.address,
            8996,
            lock_account,
        )


def get_account0():
    return _account(0)


def get_all_accounts():
    return [_account(index) for index in range(9)]


# pylint: disable=no-value-for-parameter
def _account(index: int):
    private_key = os.getenv(f"TEST_PRIVATE_KEY{index}")
    return Account.from_key(private_key=private_key)
