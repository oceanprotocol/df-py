from util import oceanutil, networkutil


def test_1():
    OCEAN = oceanutil.OCEANtoken()
    assert OCEAN.symbol().lower() == "ocean"

    
def test_2():
    OCEAN = oceanutil.OCEANtoken()
    assert OCEAN.symbol().lower() == "ocean"


def setup_function():
    networkutil.connect(networkutil.DEV_CHAINID)
    oceanutil.recordDevDeployedContracts()


def teardown_function():
    networkutil.disconnect()
