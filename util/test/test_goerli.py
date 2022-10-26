import os
import types

from enforce_typing import enforce_types

from util import networkutil

PREV = None

CHAINID = networkutil.networkToChainId("goerli")


@enforce_types
def test_chainIdToNetwork():
    network_str = networkutil.chainIdToNetwork(CHAINID)
    assert network_str == "goerli"


@enforce_types
def test_chainIdToSubgraphUri():
    uri = networkutil.chainIdToSubgraphUri(CHAINID)
    assert "subgraph.goerli.oceanprotocol.com" in uri


@enforce_types
def test_main(tmp_path):
    # brownie has a bug when trying to shut down non-ganache networks
    # details in https://github.com/eth-brownie/brownie/issues/1144
    # in file venv/lib/python3.8/site-packages/brownie/network/state.py
    #   function: _remove_contract()
    #   code: del _contract_map[contract.address]

    # This isn't a problem from cli, since it cleans up mem
    # But it is a problem for unit tests. Our workaround is to do a system call.

    ACCOUNT_ADDR = "0xc945a5a960fef1a9c3fef8593fc2446d1d7c6146"
    TOKEN_ADDR = "0xb4fbf271143f4fbf7b91a5ded31805e42b2208d6"
    fn = os.path.join(tmp_path, "out.txt")
    cmd = f"./dftool acctinfo {CHAINID} {ACCOUNT_ADDR} {TOKEN_ADDR}>{fn} 2>{fn}"
    os.system(cmd)

    s = None
    with open(fn, "r") as f:
        s = f.read()

    assert " WETH" in s, cmd


@enforce_types
def setup_module():
    global PREV

    PREV = types.SimpleNamespace()

    PREV.WEB3_INFURA_PROJECT_ID = os.environ.get("WEB3_INFURA_PROJECT_ID")

    # got this value from https://rpc.info/. We could also use our own
    os.environ["WEB3_INFURA_PROJECT_ID"] = "9aa3d95b3bc440fa88ea12eaa4456161"


@enforce_types
def teardown_module():
    global PREV

    if PREV.WEB3_INFURA_PROJECT_ID is None:
        del os.environ["WEB3_INFURA_PROJECT_ID"]
    else:
        os.environ["WEB3_INFURA_PROJECT_ID"] = PREV.WEB3_INFURA_PROJECT_ID
