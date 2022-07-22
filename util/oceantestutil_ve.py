import random

import brownie
from brownie.convert.main import to_uint
from enforce_typing import enforce_types

from util import constants, oceanutil
from util.base18 import toBase18, fromBase18

network = brownie.network

@enforce_types
def randomDeployFREsThenConsume(num_FRE: int, base_token):
    accounts = network.accounts

    # create random num_FRE.
    tups = []  # (pub_account_i, data_NFT, DT, FRE)
    for fre_i in range(num_FRE):
        if fre_i < len(accounts):
            account_i = fre_i
        else:
            account_i = random.randint(0, len(accounts))
        (data_NFT, DT, FRE) = deployDataNFTWithFRE(accounts[account_i], base_token)
        tups.append((account_i, data_NFT, DT, FRE))

# TODO - Finish other random events
# def randomLockUpVote(num_fres: int, base_token):
# def randomAllocateWeight(num_fres: int, base_token):

@enforce_types
def deployDataNFTWithFRE(from_account, token):
    data_NFT = oceanutil.createDataNFT("1", "1", from_account)
    DT = oceanutil.createDatatokenFromDataNFT("1", "1", data_NFT, from_account)

    exchangeId = oceanutil.createFREFromDatatoken(
        DT,
        token,
        10.0,
        from_account
    )

    return (data_NFT, DT, exchangeId)
