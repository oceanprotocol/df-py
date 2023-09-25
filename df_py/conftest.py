from enforce_typing import enforce_types
from eth_account import Account
import os
import pytest

from df_py.util import networkutil
from df_py.util.oceanutil import OCEAN_token, record_dev_deployed_contracts
from df_py.util.base18 import from_wei, to_wei
from df_py.util.oceanutil import get_rpc_url, get_web3


def pytest_sessionstart():
    networkutil.connect_dev()
    record_dev_deployed_contracts()
    accs = [
        Account.from_key(private_key=os.getenv(f"TEST_PRIVATE_KEY{index}"))
        for index in range(0, 8)
    ]

    # TODO: check
    # OCEAN_token().mint(accs[0], 1e24, {"from": accs[0]})
    OCEAN_token().mint(accs[0], to_wei(10000), {"from": accs[0]})


@pytest.fixture
def w3():
    w3 = get_web3(get_rpc_url("development"))
    account = Account.from_key(private_key=os.getenv("TEST_PRIVATE_KEY0"))
    w3.eth.default_account = account.address

    return w3


@pytest.fixture
def account0():
    return Account.from_key(private_key=os.getenv("TEST_PRIVATE_KEY0"))
