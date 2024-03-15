import pytest

from df_py.util import networkutil, oceantestutil
from df_py.util.base18 import to_wei
from df_py.util.oceanutil import OCEAN_token, record_dev_deployed_contracts


def pytest_sessionstart():
    return #HACK
    record_dev_deployed_contracts()
    accs = oceantestutil.get_all_accounts()
    OCEAN_token(networkutil.DEV_CHAINID).mint(
        accs[0], to_wei(10_000), {"from": accs[0]}
    )


@pytest.fixture
def w3():
    web3 = networkutil.chain_id_to_web3(8996)
    account = oceantestutil.get_account0()
    web3.eth.default_account = account.address

    return web3


@pytest.fixture
def account0():
    return oceantestutil.get_account0()


@pytest.fixture
def all_accounts():
    return oceantestutil.get_all_accounts()
