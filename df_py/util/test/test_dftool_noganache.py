import os
import subprocess
from typing import List
from unittest.mock import patch

import pytest
from enforce_typing import enforce_types

from df_py.util import dftool_arguments, dftool_module
from df_py.util.test.test_dftool_ganache import sysargs_context
from df_py.volume import csvs


@enforce_types
def test_getrate(tmp_path):
    TOKEN_SYMBOL = "OCEAN"
    ST = "2022-01-01"
    FIN = "2022-02-02"
    CSV_DIR = str(tmp_path)

    cmd = f"./dftool getrate {TOKEN_SYMBOL} {ST} {FIN} {CSV_DIR}"
    os.system(cmd)

    # test result
    assert csvs.rate_csv_filenames(CSV_DIR)


@enforce_types
@pytest.mark.skip(reason="Passing. However script executes N commands ~18m")
def test_gen_hist_data():
    os.environ["USE_TESTNET"] = "1"
    cmd = "./scripts/gen_hist_data.sh 22 round_22"
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
    # Test commands that have no args
    subargs = _get_HELP_subargs_in_dftool()
    subargs = [""] + ["badarg"] + subargs

    # these commands are intended to have no parameters
    fail_gracefully = ["help", "compile", "newacct"]

    for subarg in subargs:
        sys_argv = ["dftool", subarg]

        if subarg in ["compile", "newacct"]:
            with sysargs_context(sys_argv):
                dftool_module._do_main()
            continue

        print(f"CMD: dftool {subarg}")

        with pytest.raises(SystemExit) as excinfo:
            with sysargs_context(sys_argv):
                dftool_module._do_main()

        if subarg in fail_gracefully:
            assert excinfo.value.code == 0
        else:
            assert excinfo.value.code in [1, 2]


@enforce_types
def _get_HELP_subargs_in_dftool() -> List[str]:
    """Return e.g. ["help", "compile", "getrate", "volsym", ...]"""
    help_content = getattr(dftool_arguments, "HELP_LONG")
    s_lines = help_content.split("\n")

    subargs = []
    for s_line in s_lines:
        if "Usage:" in s_line:
            continue
        if "dftool " not in s_line:
            continue
        subarg = s_line.lstrip().split(" ")[1]  # e.g. "compile"
        subargs.append(subarg)

    assert "compile" in subargs  # postcondition
    return subargs


@enforce_types
def test_functions_exist():
    functions = _get_HELP_subargs_in_dftool()
    functions.remove("help")  # maps to help_short

    for function in functions:
        with patch("df_py.util.dftool_module.do_" + function):
            # patch can only overwrite existing functions
            # so that ensures the function exists
            pass
