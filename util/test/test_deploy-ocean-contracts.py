import brownie
import pytest

from util import oceanutil

@pytest.mark.skip(reason="reinstate when in ropsten PR")
def test1(tmp_dir):
    address_file = os.path.join(tmp_dir, "address.json")
    chainID = 0
    oceanutil.deployOceanContracts(address_file, chainID)

    #does address_file hold appropriate values?

    #can I access things like I normally do?
