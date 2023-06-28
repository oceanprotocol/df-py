from enforce_typing import enforce_types

from df_py.util import networkutil, oceanutil


@enforce_types
def test_1():
    OCEAN = oceanutil.OCEANtoken()
    assert OCEAN.symbol().lower() == "ocean"


@enforce_types
def test_2():
    OCEAN = oceanutil.OCEANtoken()
    assert OCEAN.symbol().lower() == "ocean"


@enforce_types
def setup_function():
    networkutil.connect_dev()
    oceanutil.recordDevDeployedContracts()


@enforce_types
def teardown_function():
    networkutil.disconnect()
