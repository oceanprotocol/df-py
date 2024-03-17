import pytest

from df_py.mathutil.base18 import to_wei
from df_py.web3util.networkutil import DEV_CHAINID, chain_id_to_web3
from df_py.web3util.oceanutil import OCEAN_token, record_dev_deployed_contracts
from df_py.web3util.oceantestutil import get_account0, get_all_accounts


def pytest_sessionstart():
    record_dev_deployed_contracts()
    accs = get_all_accounts()
    OCEAN_token(DEV_CHAINID).mint(accs[0], to_wei(10_000), {"from": accs[0]})


@pytest.fixture
def w3():
    web3 = chain_id_to_web3(8996)
    account = get_account0()
    web3.eth.default_account = account.address
    return web3


@pytest.fixture
def account0():
    return get_account0()


@pytest.fixture
def all_accounts():
    return get_all_accounts()
