import brownie
from enforce_typing import enforce_types

from df_py.util import networkutil, oceanutil
from df_py.util.constants import BROWNIE_PROJECT as B

accounts = None


@enforce_types
def test_deploy_ve():
    """Test deploy veOCEAN contract."""
    OCEAN = oceanutil.OCEAN_token()

    veOCEAN = B.veOcean.deploy(
        OCEAN.address, "veOCEAN", "veOCEAN", "0.1.0", {"from": accounts[0]}
    )

    assert veOCEAN.admin() == accounts[0].address


@enforce_types
def setup_function():
    networkutil.connect_dev()
    oceanutil.record_dev_deployed_contracts()
    global accounts
    accounts = brownie.network.accounts


@enforce_types
def teardown_function():
    networkutil.disconnect()
