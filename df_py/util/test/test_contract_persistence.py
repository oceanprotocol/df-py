from enforce_typing import enforce_types

from df_py.util import networkutil, oceanutil


@enforce_types
def test_1():
    OCEAN = oceanutil.OCEAN_token(networkutil.DEV_CHAINID)
    assert OCEAN.symbol().lower() == "ocean"


@enforce_types
def test_2():
    OCEAN = oceanutil.OCEAN_token(networkutil.DEV_CHAINID)
    assert OCEAN.symbol().lower() == "ocean"


@enforce_types
def setup_function():
    oceanutil.record_dev_deployed_contracts()
