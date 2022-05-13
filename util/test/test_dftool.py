import os
from enforce_typing import enforce_types
import types

from util import constants, csvs


def test_do_query(tmp_path):
    prev = _setBargeEnvvars()
    
    CHAINID = 0
    ST = 0
    FIN = "latest"
    NSAMP = 5
    CSV_DIR = str(tmp_path)
    
    cmd = f"./dftool query {CHAINID} {ST} {FIN} {NSAMP} {CSV_DIR}"
    os.system(cmd)

    assert csvs.stakesCsvFilenames(CSV_DIR)
    assert csvs.poolvolsCsvFilenames(CSV_DIR)

    _restorePrevEnvvars(prev)


def _setBargeEnvvars():
    prev = types.SimpleNamespace()
    
    prev.ADDRESS_FILE = os.environ.get('ADDRESS_FILE')
    os.environ['ADDRESS_FILE'] = os.path.expanduser(constants.BARGE_ADDRESS_FILE)
    
    prev.SUBGRAPH_URI = os.environ.get('SUBGRAPH_URI')
    os.environ['SUBGRAPH_URI'] = constants.BARGE_SUBGRAPH_URI

    return prev


def _restorePrevEnvvars(prev):
    if prev.ADDRESS_FILE is None:
        del os.environ['ADDRESS_FILE']
    else:
        os.environ['ADDRESS_FILE'] = prev.ADDRESS_FILE
        
    if prev.SUBGRAPH_URI is None:
        del os.environ['SUBGRAPH_URI']
    else:
        os.environ['SUBGRAPH_URI'] = prev.SUBGRAPH_URI

