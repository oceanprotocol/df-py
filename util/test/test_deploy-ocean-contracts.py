import brownie

from util.base18 import toBase18
from util.constants import BROWNIE_PROJECT as B
from util.oceanutil import CONTRACTS as C
from util import oceanutil

def test1():
    address_file = "foo" #FIXMe
    chainID = 0
    oceanutil.deployOceanContracts(address_file, chainID)
    
    #ensure ADDRESS_FILE (address.json path) is set to what we expect
    
    #update the values in ADDRESS_FILE


