from enforce_typing import enforce_types

from util import oceanutil, networkutil


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
    networkutil.connect(networkutil.DEV_CHAINID)
    oceanutil.recordDevDeployedContracts()


@enforce_types
def teardown_function():
    networkutil.disconnect()
