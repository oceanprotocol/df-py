import os

import pytest
from eth_account import Account

from df_py.util import networkutil, oceantestutil
from df_py.util.base18 import to_wei
from df_py.util.oceanutil import OCEAN_token, record_dev_deployed_contracts


def pytest_sessionstart():
    record_dev_deployed_contracts()
    accs = oceantestutil.get_all_accounts()

    # TODO: check
    # OCEAN_token().mint(accs[0], 1e24, {"from": accs[0]})
    OCEAN_token().mint(accs[0], to_wei(10000), {"from": accs[0]})


@pytest.fixture
def w3():
    w3 = networkutil.chain_id_to_web3(8996)
    account = oceantestutil.get_account0()
    w3.eth.default_account = account.address

    return w3


@pytest.fixture
def account0():
    return oceantestutil.get_account0()


@pytest.fixture
def all_accounts():
    return oceantestutil.get_all_accounts()
