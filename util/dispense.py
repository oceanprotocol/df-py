import csv
from enforce_typing import enforce_types
import os

from util.constants import BROWNIE_PROJECT as B
from util.base18 import fromBase18, toBase18

BATCH_SIZE = 100

@enforce_types
def dispenseFromLists(
        tos: list, values_int:list, airdrop_addr:str, from_account,
        batch_size:int=BATCH_SIZE):
    assert len(tos) == len(values_int)
    
    print("dispense: begin")
    print(f"  # addresses: {len(tos)}")
    
    airdrop = B.Airdrop.at(airdrop_addr)
    TOK = B.Simpletoken.at(airdrop.getToken())
    print(f"  Total amount: {fromBase18(sum(values_int))} {TOK.symbol()}")
    
    TOK.approve(airdrop, sum(values_int), {"from": from_account})

    N = len(tos)
    sts = list(range(N))[::batch_size] #send in batches to avoid gas issues
    for i, st in enumerate(sts):
        fin = st + batch_size
        print(f"  Batch #{(i+1)}/{len(sts)}, {len(tos[st:fin])} addresses")
        airdrop.allocate(tos[st:fin], values_int[st:fin], {"from":from_account})
    print("dispense: done")

