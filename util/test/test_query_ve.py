import time

import pytest
import brownie
from enforce_typing import enforce_types

from util import networkutil
from util.oceanutil import OCEANtoken
from util.oceantestutil import fillAccountsWithToken
from util.oceantestutil_ve import randomDeployFREsThenConsume
from util.constants import BROWNIE_PROJECT as B, CONTRACTS

account0, QUERY_ST = None, 0

CHAINID = networkutil.DEV_CHAINID


@pytest.mark.timeout(300)
def test_populateSubgraph():
    """We want to verify this is working so we can populate our subgraph."""

    fillAccountsWithToken(OCEANtoken())

    # keep deploying, until TheGraph node sees volume, or timeout
    # (assumes that with volume, everything else is there too
    for loop_i in range(1):
        print(f"loop {loop_i} start")
        assert loop_i < 5, "timeout"
        if _foundAllocationAndConsume():
            break
        randomDeployFREsThenConsume(1, OCEANtoken())

        # TODO - complete other steps to seed
        # randomLockUpVote(2, veOCEAN())
        # randomAllocateWeight(2, veAllocate())

        print(f"loop {loop_i} not successful, so sleep and re-loop")
        time.sleep(2)


# TODO - Implement ve queries
def _foundAllocationAndConsume():
    # fres = query_ve.getFREs(CHAINID)
    # allocates_at_chain = query_ve.getAllocates(fres, rng, CHAINID)
    # votingPower_at_veOCEAN = query_ve.getVotingPower(fres, rng, CHAINID)
    # votingPower_at_veDelegate = query_ve.getDelegatePower(fres, rng, CHAINID)
    # FRE_vols = query_ve.getFREVolumes(st, fin, CHAINID)
    
    # all good
    return False


@enforce_types
def setup_function():
    global OCEAN_ADDR

    networkutil.connect(CHAINID)
    global account0, QUERY_ST
    account0 = brownie.network.accounts[0]
    QUERY_ST = max(0, len(brownie.network.chain) - 200)
    
    # Init contracts
    ocean = B.Simpletoken.deploy("OCEAN", "test OCEAN", 18, 1e26, {"from": account0})
    opfcommunityfeecollector = B.OPFCommunityFeeCollector.deploy(account0, account0, {"from": account0})
    poolTemplate = B.BPool.deploy({"from": account0})
    factoryRouter = B.FactoryRouter.deploy(account0, ocean.address, poolTemplate.address, opfcommunityfeecollector.address, [], {"from": account0})
    templateERC20 = B.ERC20Template.deploy({"from": account0})
    templateERC721 = B.ERC721Template.deploy({"from": account0})
    factoryERC721 = B.ERC721Factory.deploy(templateERC721.address, templateERC20.address, factoryRouter.address, {"from": account0})
    fixedRateExchange = B.FixedRateExchange.deploy(factoryRouter.address, {"from": account0})
    ve_ocean = B.veOCEAN.deploy(ocean.address, "veOCEAN", "veOCEAN", "0.1", {"from": account0})
    ve_allocate = B.veAllocate.deploy({"from": account0})
    
    # Init constants/globals
    CONTRACTS[CHAINID] = {}
    C = CONTRACTS[CHAINID]
    C["Ocean"] = ocean
    C["ERC721Template"] = templateERC721
    C["ERC20Template"] = templateERC20
    C["PoolTemplate"] = poolTemplate
    C["Router"] = factoryRouter
    C["ERC721Factory"] = factoryERC721
    C["FixedPrice"] = fixedRateExchange
    C["veOCEAN"] = ve_ocean
    C["veAllocate"] = ve_allocate

@enforce_types
def teardown_function():
    networkutil.disconnect()
