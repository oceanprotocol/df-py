from enforce_typing import enforce_types
import pytest

from util import cleancase, approvedfilter


APPROVED_TOKEN_ADDRS = {1: ["0xocean", "0xh2o"], 2: ["0xocean2", "Oxh2o2"]}


@enforce_types
def test_stakes_fail_cleancase():
    stakes_bad = {1: {"0xoCeAn": {"0xpOolA": {"0xLp1": 1.0, "0xLP2": 2.0}}}}
    stakes_clean = {1: {"0xocean": {"0xpoola": {"0xlp1": 1.0, "0xlp2": 2.0}}}}

    with pytest.raises(AssertionError):
        approvedfilter.modStakes(APPROVED_TOKEN_ADDRS, stakes_bad)

    approvedfilter.modStakes(APPROVED_TOKEN_ADDRS, stakes_clean)


@enforce_types
def test_stakes_main():
    stakes = {
        1: {
            "0xocean": {"0xpoola": {"0xlp1": 1.0, "0xlp2": 2.0}},
            "0xh2o": {"0xpoolc": {"0xlp4": 4.0}},
            "0xfoo": {"0xpoold": {"0xlp5": 0.0}},  # filter this
        },
        2: {"0xocean2": {"0xpoole": {"0xlp6": 5.0}}},
    }
    target_stakes = {
        1: {
            "0xocean": {"0xpoola": {"0xlp1": 1.0, "0xlp2": 2.0}},
            "0xh2o": {"0xpoolc": {"0xlp4": 4.0}},
        },
        2: {"0xocean2": {"0xpoole": {"0xlp6": 5.0}}},
    }
    cleancase.assertStakes(target_stakes)

    mod_stakes = approvedfilter.modStakes(APPROVED_TOKEN_ADDRS, stakes)
    approvedfilter.assertStakes(APPROVED_TOKEN_ADDRS, mod_stakes)
    assert mod_stakes == target_stakes


@enforce_types
def test_poolvols_fail_cleancase():
    poolvols_bad = {
        1: {"0xoCeAn": {"0xpOolA": 1.0, "0xPOOLB": 2.0}},
        2: {"0xocean2": {"0xPOOLD": 4.0}},
    }
    poolvols_clean = {
        1: {"0xocean": {"0xpoola": 1.0, "0xpoolb": 2.0}},
        2: {"0xocean2": {"0xpoold": 4.0}},
    }

    with pytest.raises(AssertionError):
        approvedfilter.modPoolvols(APPROVED_TOKEN_ADDRS, poolvols_bad)

    approvedfilter.modPoolvols(APPROVED_TOKEN_ADDRS, poolvols_clean)


@enforce_types
def test_poolvols_main():
    poolvols = {
        1: {
            "0xocean": {"0xpoola": 1.0, "0xpoolb": 2.0},
            "0xh2o": {"0xpoolc": 3.0},
            "0xfoo": {"0xpoold": 4.0},  # it should filter this
        },
        2: {"0xocean2": {"0xpoole": 5.0}},
    }
    target_poolvols = {
        1: {
            "0xocean": {"0xpoola": 1.0, "0xpoolb": 2.0},
            "0xh2o": {"0xpoolc": 3.0},
        },
        2: {"0xocean2": {"0xpoole": 5.0}},
    }
    cleancase.assertPoolvols(target_poolvols)

    mod_poolvols = approvedfilter.modPoolvols(APPROVED_TOKEN_ADDRS, poolvols)
    approvedfilter.assertPoolvols(APPROVED_TOKEN_ADDRS, mod_poolvols)
    assert mod_poolvols == target_poolvols
