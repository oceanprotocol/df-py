from enforce_typing import enforce_types

from df_py.util import oceanutil, networkutil
from df_py.util.contract_base import ContractBase


@enforce_types
def test_deploy_ve(w3, account0):
    """Test deploy veOCEAN contract."""
    oceanutil.record_dev_deployed_contracts()
    OCEAN = oceanutil.OCEAN_token(networkutil.DEV_CHAINID)

    veOCEAN = ContractBase(
        w3,
        "ve/veOcean",
        constructor_args=[OCEAN.address, "veOCEAN", "veOCEAN", "0.1.0"],
    )

    assert veOCEAN.admin() == account0.address
