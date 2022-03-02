#!/usr/bin/env python

import csv
import os
import sys

import brownie

from util.base18 import toBase18, fromBase18

BROWNIE_PROJECT = brownie.project.load("./", name="MyProject")

NETWORKS = ['development', 'eth_mainnet'] #development = ganache

# ========================================================================
HELP_MAIN = """Vesting wallet - main help

Usage: vw fund|release|..
  vw fund - send funds with vesting wallet
  vw batch - batch send funds via vesting wallets
  vw release - request vesting wallet to release funds
  vw token - create token, for testing
  vw mine - force chain to pass time (ganache only)

  vw accountinfo - info about an account
  vw walletinfo - info about a vesting wallet
  vw help - this message

Transactions are signed with envvar 'VW_KEY`.

Test flow, local net,  1 wallet : token -> fund   -> mine -> release
                       N wallets: token -> batch  -> mine -> release, rel, ..
Test flow, remote net, 1 wallet : token -> fund   -> (wait) -> release
                       N wallets: token -> batch  -> (wait) -> release, rel, ..
Prod flow, remote net, 1 wallet : fund -> (wait)  -> release
                       N wallets: batch -> (wait) -> release, rel, .."""
def show_help():
    print(HELP_MAIN)
    sys.exit(0)
    
# ========================================================================
def do_fund():
    HELP_FUND = f"""Vesting wallet - send funds with vesting wallet

Usage: vw fund NETWORK TOKEN_ADDR LOCK_TIME AMT TO_ADDR

  NETWORK -- one of {NETWORKS}
  TOKEN_ADDR -- address of token being sent. Eg 0x967da4048cd07ab37855c090aaf366e4ce1b9f48 for OCEAN on eth mainnet
  LOCK_TIME -- Eg '10' (10 seconds) or '63113852' (2 years)
  AMT -- e.g. '1000' (base-18, not wei)
  TO_ADDR -- address of beneficiary"""

    if len(sys.argv) not in [7]:
        print(HELP_FUND)
        sys.exit(0)

    # extract inputs
    assert sys.argv[1] == "fund"
    NETWORK = sys.argv[2]
    TOKEN_ADDR = sys.argv[3]
    LOCK_TIME = int(sys.argv[4])
    AMT = float(sys.argv[5])
    TO_ADDR = sys.argv[6]
    print(
        f"Arguments: NETWORK={NETWORK}, TOKEN_ADDR={TOKEN_ADDR}"
        f", LOCK_TIME={LOCK_TIME}, AMT={AMT}, TO_ADDR={TO_ADDR}"
    )
    
    brownie.network.connect(NETWORK) 
    _create_and_fund_vesting_wallet(NETWORK, TOKEN_ADDR, LOCK_TIME, AMT, TO_ADDR)
    
# ========================================================================
def do_batch():
    HELP_FUND = f"""Vesting wallet - batch send funds via vesting wallets

Usage: vw batch NETWORK TOKEN_ADDR LOCK_TIME CSV

  NETWORK -- one of {NETWORKS}
  TOKEN_ADDR -- address of token being sent. Eg 0x967da4048cd07ab37855c090aaf366e4ce1b9f48 for OCEAN on eth mainnet
  LOCK_TIME -- Eg '10' (10 seconds) or '63113852' (2 years)
  CSV -- csv file, where each row has: amt, address of beneficiary"""

    if len(sys.argv) not in [6]:
        print(HELP_FUND)
        sys.exit(0)

    # extract inputs
    assert sys.argv[1] == "batch"
    NETWORK = sys.argv[2]
    TOKEN_ADDR = sys.argv[3]
    LOCK_TIME = int(sys.argv[4])
    CSV = sys.argv[5]
    
    print(
        f"Arguments: NETWORK={NETWORK}, TOKEN_ADDR={TOKEN_ADDR}"
        f", LOCK_TIME={LOCK_TIME}, CSV={CSV}"
    )

    brownie.network.connect(NETWORK)
    TO_ADDRs, VWs = [], []
    with open(CSV, 'r') as csv_file:
        reader = csv.reader(csv_file)
        for row in reader:
            (AMT, TO_ADDR) = row
            print(f"call vw fund for TO_ADDR: {TO_ADDR[:5]}..")
            
            VW = _create_and_fund_vesting_wallet(
                NETWORK, TOKEN_ADDR, LOCK_TIME, float(AMT), TO_ADDR.strip())
            TO_ADDRs.append(TO_ADDR)
            VWs.append(VW)
            
    print(f"Done batch. TO_ADDR --> WALLET_ADDR:")
    for (TO_ADDR, VW) in zip(TO_ADDRs, VWs):
        print(f"{TO_ADDR} --> {VW.address}")

def _create_and_fund_vesting_wallet(NETWORK, TOKEN_ADDR, LOCK_TIME, AMT, TO_ADDR):
    """helper to do_fund() and do_batch()"""
    
    #brownie setup
    accounts = brownie.network.accounts
    chain = brownie.network.chain

    #
    from_account = _getPrivateAccount()

    #grab token
    token = BROWNIE_PROJECT.Simpletoken.at(TOKEN_ADDR)
    print(f"Token symbol: {token.symbol()}")

    #deploy vesting wallet
    print("Deploy vesting wallet...")
    start_timestamp = chain[-1].timestamp + 5  # magic number
    vesting_wallet = BROWNIE_PROJECT.VestingWallet.deploy(
        TO_ADDR, start_timestamp, LOCK_TIME, {"from": from_account}
    )

    #send tokens to vesting wallet
    print("Fund vesting wallet...")
    token.transfer(vesting_wallet, toBase18(AMT), {"from": from_account})

    print(f"Done. Vesting wallet address: {vesting_wallet.address}")

    return vesting_wallet


# ========================================================================
def do_release():
    HELP_RELEASE = f"""Vesting wallet - request vesting wallet to release funds

Usage: vw release NETWORK TOKEN_ADDR WALLET_ADDR

  NETWORK -- one of {NETWORKS}
  TOKEN_ADDR -- e.g. '0x123..'
  WALLET_ADDR -- vesting wallet, e.g. '0x987...'"""
    if len(sys.argv) not in [5]:
        print(HELP_RELEASE)
        sys.exit(0)

    # extract inputs
    assert sys.argv[1] == "release"
    NETWORK = sys.argv[2]
    TOKEN_ADDR = sys.argv[3]
    WALLET_ADDR = sys.argv[4]

    print(f"Arguments: NETWORK={NETWORK}, TOKEN_ADDR={TOKEN_ADDR}"
          f", WALLET_ADDR={WALLET_ADDR}"
    )

    #brownie setup
    brownie.network.connect(NETWORK) 
    accounts = brownie.network.accounts
    from_account = _getPrivateAccount()

    #release the token
    vesting_wallet = BROWNIE_PROJECT.VestingWallet.at(WALLET_ADDR)
    vesting_wallet.release(TOKEN_ADDR, {"from": from_account})
    
    print("Funds have been released.")


# ========================================================================
def do_token():
    HELP_TOKEN = f"""Vesting wallet create test token

Usage: vw token NETWORK

NETWORK -- one of {NETWORKS}"""
    if len(sys.argv) not in [3]:
        print(HELP_TOKEN)
        sys.exit(0)

    # extract inputs
    assert sys.argv[1] == "token"
    NETWORK = sys.argv[2]

    print(f"Arguments: NETWORK={NETWORK}")

    #brownie setup
    brownie.network.connect(NETWORK) 
    accounts = brownie.network.accounts

    #
    from_account = _getPrivateAccount()

    #deploy wallet
    token = BROWNIE_PROJECT.Simpletoken.deploy(
        "TST", "Test Token", 18, 1e21, {"from": from_account}
    )
    print(f"Token '{token.symbol()}' deployed at address: {token.address}")
    
# ========================================================================
def do_mine():
    HELP_MINE = f"""Vesting wallet - force chain to pass time (ganache only)

Usage: vw mine BLOCKS TIMEDELTA

  BLOCKS -- e.g. 3
  TIMEDELTA -- e.g. 100"""
    if len(sys.argv) not in [4]:
        print(HELP_MINE)
        sys.exit(0)

    # extract inputs
    assert sys.argv[1] == "mine"
    BLOCKS = int(sys.argv[2])
    TIMEDELTA = int(sys.argv[3])

    print(f"Arguments: BLOCKS={BLOCKS}, TIMEDELTA={TIMEDELTA}")

    #brownie setup
    NETWORK = 'development' #hardcoded bc it's the only one we can force
    brownie.network.connect(NETWORK) 
    accounts = brownie.network.accounts
    chain = brownie.network.chain
    from_account = _getPrivateAccount()

    #make time pass
    chain.mine(blocks=BLOCKS, timedelta=TIMEDELTA)
    
    print("Done.")


# ========================================================================
def show_accountinfo():
    HELP_ACCOUNTINFO = f"""Vesting wallet - info about an account

Usage: vw accountinfo NETWORK TOKEN_ADDR ACCOUNT_ADDR

  NETWORK -- one of {NETWORKS}
  TOKEN_ADDR -- e.g. '0x123..'
  ACCOUNT_ADDR -- account address, e.g. '0x987...'"""
    if len(sys.argv) not in [5]:
        print(HELP_ACCOUNTINFO)
        sys.exit(0)

    # extract inputs
    assert sys.argv[1] == "accountinfo"
    NETWORK = sys.argv[2]
    TOKEN_ADDR = sys.argv[3]
    ACCOUNT_ADDR = sys.argv[4]

    print(f"Arguments: NETWORK={NETWORK}, TOKEN_ADDR={TOKEN_ADDR}"
          f", ACCOUNT_ADDR={ACCOUNT_ADDR}"
    )

    #brownie setup
    brownie.network.connect(NETWORK)

    #release the token
    token = BROWNIE_PROJECT.Simpletoken.at(TOKEN_ADDR)
    balance = token.balanceOf(ACCOUNT_ADDR)
    print(f"For account {ACCOUNT_ADDR[:5]}.., token '{token.symbol()}':")
    print(f"  balance of token : {fromBase18(balance)} {token.symbol()}")

# ========================================================================
def show_walletinfo():
    HELP_WALLETINFO = f"""Vesting wallet - show info about a vesting wallet

Usage: vw walletinfo NETWORK TOKEN_ADDR WALLET_ADDR

  NETWORK -- one of {NETWORKS}
  TOKEN_ADDR -- e.g. '0x123..'
  WALLET_ADDR -- vesting wallet address"""
    if len(sys.argv) not in [5]:
        print(HELP_WALLETINFO)
        sys.exit(0)

    # extract inputs
    assert sys.argv[1] == "walletinfo"
    NETWORK = sys.argv[2]
    TOKEN_ADDR = sys.argv[3]
    WALLET_ADDR = sys.argv[4]

    print(f"Arguments: NETWORK={NETWORK}, TOKEN_ADDR={TOKEN_ADDR}"
          f", WALLET_ADDR={WALLET_ADDR}"
    )

    #brownie setup
    brownie.network.connect(NETWORK)
    chain = brownie.network.chain

    #release the token
    token = BROWNIE_PROJECT.Simpletoken.at(TOKEN_ADDR)
    wallet = BROWNIE_PROJECT.VestingWallet.at(WALLET_ADDR)
    amt_vested = wallet.vestedAmount(token.address, chain[-1].timestamp)
    amt_released = wallet.released(token.address)
    print(f"For vesting wallet {WALLET_ADDR[:5]}.., token '{token.symbol()}':")
    print(f"  beneficiary: {wallet.beneficiary()[:5]}..")
    print(f"  start: {wallet.start()} (compare to current chain time of {chain[-1].timestamp})")
    print(f"  duration: {wallet.duration()} s")
    print(f"  amt vested: {fromBase18(amt_vested)} {token.symbol()}")
    print(f"  amt released: {fromBase18(amt_released)} {token.symbol()}")

# ========================================================================
def _getPrivateAccount():
    private_key = os.getenv('VW_KEY')
    account = brownie.network.accounts.add(private_key=private_key)
    print(f"For private key VW_KEY, address is: {account.address}")
    return account

# ========================================================================
# main
def do_main():
    if len(sys.argv) == 1 or sys.argv[1] == "help":
        show_help()

    #write actions
    elif sys.argv[1] == "token":
        do_token()
    elif sys.argv[1] == "fund":
        do_fund()
    elif sys.argv[1] == "batch":
        do_batch()
    elif sys.argv[1] == "mine":
        do_mine()
    elif sys.argv[1] == "release":
        do_release()

    #read actions
    elif sys.argv[1] == "accountinfo":
        show_accountinfo()
    elif sys.argv[1] == "walletinfo":
        show_walletinfo()
    else:
        show_help()

if __name__ == "__main__":
    do_main()
