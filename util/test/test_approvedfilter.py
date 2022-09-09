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
            "0xOCEAN": {"0xlp1": 1.0, "0xlp2": 2.0},
            "0xH2O": {"0xlp4": 4.0},
            "0xfoo": {"0xlp5": 0.0},
        },
        2: {"0xocean2": {"0xlp6": 5.0}},
    }
    target_allocations = {
        1: {
            "0xocean": {"0xlp1": 1.0, "0xlp2": 2.0},
            "0xh2o": {"0xlp4": 4.0},
            "0xfoo": {"0xlp5": 0.0},
        },
        2: {"0xocean2": {"0xlp6": 5.0}},
    }
    mod_allocations = cleancase.modAllocations(allocations)
    cleancase.assertAllocations(target_allocations)

    mod_allocations = approvedfilter.modAllocations(mod_allocations)
    approvedfilter.assertAllocations(mod_allocations)
    assert mod_allocations == target_allocations


@enforce_types
def test_nftvols_fail_cleancase():
    nftvols_bad = {
        1: {"0xoCeAn": {"0xnFtA": 1.0, "0xNFTB": 2.0}},
        2: {"0xocean2": {"0xNFTD": 4.0}},
    }
    nftvols_clean = {
        1: {"0xocean": {"0xnfta": 1.0, "0xnftb": 2.0}},
        2: {"0xocean2": {"0xnftd": 4.0}},
    }

    with pytest.raises(AssertionError):
        approvedfilter.modNFTvols(APPROVED_TOKEN_ADDRS, nftvols_bad)

    approvedfilter.modNFTvols(APPROVED_TOKEN_ADDRS, nftvols_clean)


@enforce_types
def test_nftvols_main():
    nftvols = {
        1: {
            "0xocean": {"0xnfta": 1.0, "0xnftb": 2.0},
            "0xh2o": {"0xnftc": 3.0},
            "0xfoo": {"0xnftd": 4.0},  # it should filter this
        },
        2: {"0xocean2": {"0xnfte": 5.0}},
    }
    target_nftvols = {
        1: {
            "0xocean": {"0xnfta": 1.0, "0xnftb": 2.0},
            "0xh2o": {"0xnftc": 3.0},
        },
        2: {"0xocean2": {"0xnfte": 5.0}},
    }
    cleancase.assertNFTvols(target_nftvols)

    mod_nftvols = approvedfilter.modNFTvols(APPROVED_TOKEN_ADDRS, nftvols)
    approvedfilter.assertNFTvols(APPROVED_TOKEN_ADDRS, mod_nftvols)
    assert mod_nftvols == target_nftvols
