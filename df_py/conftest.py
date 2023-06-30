import brownie
import pytest
from enforce_typing import enforce_types

from df_py.util import networkutil
from df_py.util.oceanutil import OCEAN_token, record_dev_deployed_contracts


@enforce_types
@pytest.fixture
def network_setup_and_teardown():
    networkutil.connect_dev()

    # everyting before the yield is run before the test
    # everything after the yield is run after the test
    # https://stackoverflow.com/a/61647454
    yield

    networkutil.disconnect()


def pytest_sessionstart():
    networkutil.connect_dev()
    record_dev_deployed_contracts()
    accs = brownie.network.accounts
    OCEAN_token().mint(accs[0], 1e24, {"from": accs[0]})
