from enforce_typing import enforce_types

from df_py.web3util.networkutil import DEV_CHAINID
from df_py.web3util.oceanutil import OCEAN_token, record_dev_deployed_contracts


@enforce_types
def test_1():
    OCEAN = OCEAN_token(DEV_CHAINID)
    assert OCEAN.symbol().lower() == "ocean"


@enforce_types
def test_2():
    OCEAN = OCEAN_token(DEV_CHAINID)
    assert OCEAN.symbol().lower() == "ocean"


@enforce_types
def setup_function():
    record_dev_deployed_contracts()
