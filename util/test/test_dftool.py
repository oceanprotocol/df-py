import os
from enforce_typing import enforce_types
import types

from util import constants, csvs

PREV = None

def test_do_query(tmp_path):
    CHAINID = 0
    ST = 0
    FIN = "latest"
    NSAMP = 5
    CSV_DIR = str(tmp_path)
    
    cmd = f"./dftool query {CHAINID} {ST} {FIN} {NSAMP} {CSV_DIR}"
    os.system(cmd)

    assert csvs.stakesCsvFilenames(CSV_DIR)
    assert csvs.poolvolsCsvFilenames(CSV_DIR)

def setup_module():
    """This automatically gets called at the beginning of each test"""
    global PREV
    PREV = types.SimpleNamespace()
    
    PREV.ADDRESS_FILE = os.environ.get('ADDRESS_FILE')
    os.environ['ADDRESS_FILE'] = \
        os.path.expanduser(constants.BARGE_ADDRESS_FILE)
    
    PREV.SUBGRAPH_URI = os.environ.get('SUBGRAPH_URI')
    os.environ['SUBGRAPH_URI'] = constants.BARGE_SUBGRAPH_URI


def teardown_module():
    """This automatically gets called at the end of each test"""
    global PREV
    if PREV.ADDRESS_FILE is None:
        del os.environ['ADDRESS_FILE']
    else:
        os.environ['ADDRESS_FILE'] = PREV.ADDRESS_FILE
        
    if PREV.SUBGRAPH_URI is None:
        del os.environ['SUBGRAPH_URI']
    else:
        os.environ['SUBGRAPH_URI'] = PREV.SUBGRAPH_URI

