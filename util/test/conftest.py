from enforce_typing import enforce_types

import pytest
import brownie

from util import networkutil
from util.oceanutil import OCEANtoken, recordDevDeployedContracts


@enforce_types
@pytest.fixture
def network_setup_and_teardown():
    networkutil.connect(networkutil.DEV_CHAINID)

    # everyting before the yield is run before the test
    # everything after the yield is run after the test
    # https://stackoverflow.com/a/61647454
    yield

    networkutil.disconnect()


def pytest_sessionstart():
    networkutil.connect(networkutil.DEV_CHAINID)
    recordDevDeployedContracts()
    accs = brownie.network.accounts
    OCEANtoken().mint(accs[0], 1e24, {"from": accs[0]})
