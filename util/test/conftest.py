from enforce_typing import enforce_types

from util import networkutil


@enforce_types
@pytest.fixture
def network_setup_and_teardown():
    networkutil.connect(networkutil.DEV_CHAINID)

    # everyting before the yield is run before the test
    # everything after the yield is run after the test
    # https://stackoverflow.com/a/61647454
    yield

    networkutil.disconnect()
