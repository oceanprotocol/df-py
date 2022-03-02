#!/usr/bin/env python 

import brownie

BROWNIE_PROJECT = brownie.project.load("./", name="MyProject")

brownie.network.connect("development") #development = ganache

accounts = brownie.network.accounts
chain = brownie.network.chain

def do_main():
    wallet = vesting_wallet(
        to_account=accounts[1], duration_seconds=10, from_account=accounts[0])

    assert wallet.beneficiary() == accounts[1].address
    assert wallet.start() > chain[-1].timestamp
    assert wallet.duration() == 10
    assert wallet.released() == 0


def vesting_wallet(to_account, duration_seconds, from_account):
    start_timestamp = chain[-1].timestamp + 5  # magic number
    wallet = BROWNIE_PROJECT.VestingWallet.deploy(
        to_account, start_timestamp, duration_seconds, {"from": from_account}
    )
    return wallet


if __name__== '__main__':
    do_main()
