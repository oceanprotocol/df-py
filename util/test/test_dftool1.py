# test_dftool1 - doesn't need network / brownie
# test_dftool2 - needs network/brownie with light setup
# test_dftool3 - needs network/brownie with heavy setup

import os
import subprocess

from enforce_typing import enforce_types

from util import csvs, networkutil

CHAINID = networkutil.DEV_CHAINID


@enforce_types
def test_nftinfo(tmp_path):
    # insert fake inputs:
    # <nothing to insert>

    # main cmd
    FIN = "2022-02-02"
    CSV_DIR = str(tmp_path)

    cmd = f"./dftool nftinfo {CSV_DIR} {CHAINID} {FIN}"
    os.system(cmd)

    # test result
    assert csvs.nftinfoCsvFilename(CSV_DIR, CHAINID)


@enforce_types
def test_getrate(tmp_path):
    # insert fake inputs:
    # <nothing to insert>

    # main cmd
    TOKEN_SYMBOL = "OCEAN"
    _ST = "2022-01-01"
    FIN = "2022-02-02"
    CSV_DIR = str(tmp_path)

    cmd = f"./dftool getrate {TOKEN_SYMBOL} {_ST} {FIN} {CSV_DIR}"
    os.system(cmd)

    # test result
    assert csvs.rateCsvFilenames(CSV_DIR)


@enforce_types
def test_calc(tmp_path):
    CSV_DIR = str(tmp_path)
    OCEAN_addr = "0x967da4048cd07ab37855c090aaf366e4ce1b9f48"

    # insert fake csvs
    allocations = {CHAINID: {"0xnft_addra": {"0xlp_addr1": 1.0}}}
    csvs.saveAllocationCsv(allocations, CSV_DIR)

    nftvols_at_chain = {OCEAN_addr: {"0xnft_addra": 1.0}}
    csvs.saveNftvolsCsv(nftvols_at_chain, CSV_DIR, CHAINID)

    creators_at_chain = {"0xnft_addra": "0xlp_addr1"}
    csvs.saveCreatorsCsv(creators_at_chain, CSV_DIR, CHAINID)

    vebals = {"0xlp_addr1": 1.0}
    locked_amt = {"0xlp_addr1": 10.0}
    unlock_time = {"0xlp_addr1": 1}
    csvs.saveVebalsCsv(vebals, locked_amt, unlock_time, CSV_DIR)

    symbols_at_chain = {OCEAN_addr: "OCEAN"}
    csvs.saveSymbolsCsv(symbols_at_chain, CSV_DIR, CHAINID)

    csvs.saveRateCsv("OCEAN", 0.50, CSV_DIR)

    # main cmd
    TOT_OCEAN = 1000.0
    cmd = f"./dftool calc {CSV_DIR} {TOT_OCEAN}"
    os.system(cmd)

    # test result
    rewards_csv = csvs.rewardsperlpCsvFilename(CSV_DIR, "OCEAN")
    assert os.path.exists(rewards_csv)


@enforce_types
def test_manyrandom():
    cmd = f"./dftool manyrandom {networkutil.DEV_CHAINID}"
    output_s = ""
    with subprocess.Popen(
        cmd, shell=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT
    ) as proc:
        while proc.poll() is None:
            output_s += proc.stdout.readline().decode("ascii")
    return_code = proc.wait()
    assert return_code == 0, f"Error. \n{output_s}"


@enforce_types
def test_noarg_commands():
    # Test commands that have no args. They're usually help commands;
    # sometimes they do the main work (eg compile).
    argv1s = [
        "",
        "query",
        "volsym",
        "getrate",
        "calc",
        "dispense",
        "dispense_active",
        "querymany",
        "compile",
        "manyrandom",
        "newdfrewards",
        "mine",
        "newacct",
        "newtoken",
        "acctinfo",
        "chaininfo",
    ]
    for argv1 in argv1s:
        print(f"Test dftool {argv1}")
        cmd = f"./dftool {argv1}"

        output_s = ""
        with subprocess.Popen(
            cmd, shell=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT
        ) as proc:
            while proc.poll() is None:
                output_s += proc.stdout.readline().decode("ascii")

        return_code = proc.wait()
        assert return_code == 0, f"'dftool {argv1}' failed. \n{output_s}"
