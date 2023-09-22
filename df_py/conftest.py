from enforce_typing import enforce_types
from eth_account import Account
import os

from df_py.util import networkutil
from df_py.util.oceanutil import OCEAN_token, record_dev_deployed_contracts


def pytest_sessionstart():
    networkutil.connect_dev()
    record_dev_deployed_contracts()
    accs = [
        Account.from_key(private_key=os.getenv(f"TEST_PRIVATE_KEY{index}"))
        for index in range(0, 8)
    ]

    # TODO: check
    # OCEAN_token().mint(accs[0], 1e24, {"from": accs[0]})
    OCEAN_token().mint(accs[0], 1, {"from": accs[0]})
