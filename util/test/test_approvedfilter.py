from enforce_typing import enforce_types
import pytest

from util import cleancase, approvedfilter


APPROVED_TOKEN_ADDRS = {1: ["0xocean", "0xh2o"], 2: ["0xocean2", "Oxh2o2"]}


@enforce_types
def test_allocation_fail_cleancase():
    allocations_bad = {1: {"0xoCeAn": {"0xLp1": 1.0, "0xLP2": 2.0}}}
    allocations_clean = {1: {"0xocean": {"0xlp1": 1.0, "0xlp2": 2.0}}}

    with pytest.raises(AssertionError):
        approvedfilter.modAllocations(allocations_bad)

    approvedfilter.modAllocations(allocations_clean)


@enforce_types
def test_allocations_main():
    allocations = {
        1: {
            "0xocean": {"0xlp1": 1.0, "0xlp2": 2.0},
            "0xh2o": {"0xlp4": 4.0},
            "0xfoo": {"0xlp5": 0.0},  # filter this
        },
        2: {"0xocean2": {"0xlp6": 5.0}},
    }
    target_allocations = {
        1: {
            "0xocean": {"0xlp1": 1.0, "0xlp2": 2.0},
            "0xh2o": {"0xlp4": 4.0},
        },
        2: {"0xocean2": {"0xlp6": 5.0}},
    }
    cleancase.assertAllocations(target_allocations)

    mod_allocations = approvedfilter.modAllocations(allocations)
    approvedfilter.assertAllocations(APPROVED_TOKEN_ADDRS, mod_allocations)
    assert mod_allocations == target_allocations


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
        approvedfilter.modNFTvols(APPROVED_TOKEN_ADDRS, poolvols_bad)

    approvedfilter.modNFTvols(APPROVED_TOKEN_ADDRS, poolvols_clean)


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
    cleancase.assertNFTvols(target_poolvols)

    mod_poolvols = approvedfilter.modNFTvols(APPROVED_TOKEN_ADDRS, poolvols)
    approvedfilter.assertPoolvols(APPROVED_TOKEN_ADDRS, mod_poolvols)
    assert mod_poolvols == target_poolvols
