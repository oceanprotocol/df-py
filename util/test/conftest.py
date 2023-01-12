from enforce_typing import enforce_types

import brownie

from util import networkutil
from util.oceanutil import OCEANtoken, recordDevDeployedContracts


def pytest_sessionstart():
    networkutil.connect(networkutil.DEV_CHAINID)
    recordDevDeployedContracts()
    accs = brownie.network.accounts
    OCEANtoken().mint(accs[0], 1e24, {"from": accs[0]})
