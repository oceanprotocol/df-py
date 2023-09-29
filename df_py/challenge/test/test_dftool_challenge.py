import os
from typing import Optional
from unittest.mock import patch

import pytest
from enforce_typing import enforce_types
from eth_account import Account

from df_py.challenge import csvs
from df_py.util import dftool_module, networkutil, oceantestutil, oceanutil
from df_py.util.base18 import to_wei
from df_py.util.networkutil import chain_id_to_web3, send_ether
from df_py.util.test.test_dftool_ganache import sysargs_context

PREV, DFTOOL_ACCT = {}, None

CHAINID = networkutil.DEV_CHAINID
ADDRESS_FILE = networkutil.chain_id_to_address_file(CHAINID)


@enforce_types
def test_empty_deadline(tmp_path, monkeypatch):
    monkeypatch.setenv("MUMBAI_RPC_URL", "http://localhost:8545")
    _test(tmp_path, DEADLINE=None)


@enforce_types
def test_deadline_none_string(tmp_path, monkeypatch):
    monkeypatch.setenv("MUMBAI_RPC_URL", "http://localhost:8545")
    _test(tmp_path, DEADLINE="None")


@enforce_types
def test_explicit_deadline(tmp_path, monkeypatch):
    monkeypatch.setenv("MUMBAI_RPC_URL", "http://localhost:8545")
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
    with patch("df_py.util.dftool_module.record_deployed_contracts"):
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

    accounts = [
        Account.from_key(private_key=os.getenv(f"TEST_PRIVATE_KEY{index}"))
        for index in range(0, 8)
    ]
    oceanutil.record_dev_deployed_contracts()
    oceantestutil.fill_accounts_with_OCEAN(accounts)

    w3 = chain_id_to_web3(8996)
    DFTOOL_ACCT = w3.eth.account.create()

    send_ether(w3, accounts[0], DFTOOL_ACCT.address, to_wei(0.001))

    for envvar in [
        "DFTOOL_KEY",
        "ADDRESS_FILE",
        "SECRET_SEED",
    ]:
        PREV[envvar] = os.environ.get(envvar)

    os.environ["DFTOOL_KEY"] = DFTOOL_ACCT._private_key.hex()
    os.environ["ADDRESS_FILE"] = ADDRESS_FILE
    os.environ["SECRET_SEED"] = "1234"


@enforce_types
def teardown_function():
    global PREV
    for envvar, envval in PREV.items():
        if envval is None:
            del os.environ[envvar]
        else:
            os.environ[envvar] = envval
    PREV = {}
