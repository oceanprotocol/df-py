import os

from enforce_typing import enforce_types

from util import networkutil

CHAINID = networkutil.networkToChainId("rinkeby")


@enforce_types
def test_chainIdToNetwork():
    network_str = networkutil.chainIdToNetwork(CHAINID)
    assert network_str == "rinkeby"


@enforce_types
def test_chainIdToSubgraphUri():
    uri = networkutil.chainIdToSubgraphUri(CHAINID)
    assert "subgraph.rinkeby.oceanprotocol.com" in uri


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
    TOKEN_ADDR = "0xddea378a6ddc8afec82c36e9b0078826bf9e68b6"
    fn = os.path.join(tmp_path, "out.txt")
    cmd = f"./dftool acctinfo {CHAINID} {ACCOUNT_ADDR} {TOKEN_ADDR}>{fn} 2>{fn}"
    os.system(cmd)

    f = open(fn, "r")
    s = f.read()
    f.close()
    assert "62000.00000000001 ZRX" in s
