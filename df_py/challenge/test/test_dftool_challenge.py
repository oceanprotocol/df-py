import os
from typing import Optional
from unittest.mock import patch

import brownie
import pytest
from enforce_typing import enforce_types

from df_py.challenge import csvs
from df_py.util import dftool_module, networkutil, oceantestutil, oceanutil
from df_py.util.base18 import to_wei
from df_py.util.test.test_dftool_ganache import sysargs_context

PREV, DFTOOL_ACCT = {}, None

CHAINID = networkutil.DEV_CHAINID
ADDRESS_FILE = networkutil.chain_id_to_address_file(CHAINID)


@enforce_types
def test1(tmp_path):
    _test(tmp_path, DEADLINE=None)


@enforce_types
def test2(tmp_path):
    _test(tmp_path, DEADLINE="None")


@enforce_types
def test3(tmp_path):
    _test(tmp_path, DEADLINE="2023-05-03_23:59")


@enforce_types
def _test(tmp_path, DEADLINE: Optional[str]):
    # build base cmd
    CSV_DIR = str(tmp_path)

    sysargs = ["dftool", "challenge_data", CSV_DIR]

    # DEADLINE option to cmd as needed
    if DEADLINE is not None:
        sysargs.append(f"--DEADLINE={DEADLINE}")

    # main call

    # targets
    (target_from_addrs, target_nft_addrs, target_nmses,) = (
        ["0xfrom1", "0xfrom2"],
        ["0xnft1", "0xnft2"],
        [0.2, 1.0],
    )

    # Mock the connection, use test data
    with patch("df_py.util.dftool_module.recordDeployedContracts"):
        with patch.object(dftool_module.judge, "get_challenge_data") as mock:
            mock.return_value = (target_from_addrs, target_nft_addrs, target_nmses)
            with sysargs_context(sysargs):
                dftool_module.do_challenge_data()

    # test result
    (from_addrs, nft_addrs, nmses) = csvs.load_challenge_data_csv(CSV_DIR)

    assert len(from_addrs) == len(nft_addrs) == len(nmses)
    assert sorted(nmses) == nmses

    assert from_addrs == target_from_addrs
    assert nft_addrs == target_nft_addrs
    assert nmses == target_nmses


@enforce_types
def test_challenge_help():
    with pytest.raises(SystemExit):
        with sysargs_context(["dftool", "challenge_data"]):
            dftool_module.do_challenge_data()


@enforce_types
def setup_function():
    global PREV, DFTOOL_ACCT

    networkutil.connect(CHAINID)
    accounts = brownie.network.accounts
    oceanutil.recordDevDeployedContracts()
    oceantestutil.fill_accounts_with_OCEAN()

    DFTOOL_ACCT = accounts.add()
    accounts[0].transfer(DFTOOL_ACCT, to_wei(0.001))

    for envvar in [
        "DFTOOL_KEY",
        "ADDRESS_FILE",
        "SECRET_SEED",
        "WEB3_INFURA_PROJECT_ID",
    ]:
        PREV[envvar] = os.environ.get(envvar)

    os.environ["DFTOOL_KEY"] = DFTOOL_ACCT.private_key
    os.environ["ADDRESS_FILE"] = ADDRESS_FILE
    os.environ["SECRET_SEED"] = "1234"
    os.environ["WEB3_INFURA_PROJECT_ID"] = "9aa3d95b3bc440fa88ea12eaa4456161"


@enforce_types
def teardown_function():
    networkutil.disconnect()

    global PREV
    for envvar, envval in PREV.items():
        if envval is None:
            del os.environ[envvar]
        else:
            os.environ[envvar] = envval
    PREV = {}
