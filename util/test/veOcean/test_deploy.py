import brownie
from enforce_typing import enforce_types
from util import networkutil, oceanutil

from util.constants import BROWNIE_PROJECT as B
from util.base18 import toBase18

accounts = None


@enforce_types
def test_deploy_ve():
    """sending native tokens to dfrewards contract should revert"""
    OCEAN = oceanutil.OCEANtoken()

    veOCEAN = B.veOCEAN.deploy(
        OCEAN.address, "veOCEAN", "veOCEAN", "0.1.0", {"from": accounts[0]}
    )

    assert veOCEAN.admin() == accounts[0].address


@enforce_types
def setup_function():
    networkutil.connect(networkutil.DEV_CHAINID)
    oceanutil.recordDevDeployedContracts()
    global accounts
    accounts = brownie.network.accounts
