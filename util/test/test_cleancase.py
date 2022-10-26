from enforce_typing import enforce_types
import pytest

from util import cleancase


@enforce_types
def test_tuple():  # super-basic test
    tup = cleancase.modTuple({}, {}, {})
    assert len(tup) == 3


@enforce_types
def test_allocations():
    allocations = {
        1: {
            "0xpOolA": {"0xLp1": 1.0, "0xLP2": 1.0},
            "0xPOOLB": {"0xLP3": 1.0},
            "0xPOoLC": {"0xlP4": 1.0},
        },
        2: {"0xPOOLD": {"0xLP5": 1.0}},
    }
    target_allocations = {
        1: {
            "0xpoola": {"0xlp1": 1.0, "0xlp2": 1.0},
            "0xpoolb": {"0xlp3": 1.0},
            "0xpoolc": {"0xlp4": 1.0},
        },
        2: {"0xpoold": {"0xlp5": 1.0}},
    }

    with pytest.raises(AssertionError):
        cleancase.assertAllocations(allocations)

    mod_stakes = cleancase.modAllocations(allocations)
    cleancase.assertAllocations(mod_stakes)
    assert mod_stakes == target_allocations


@enforce_types
def test_allocations_fail():
    allocations = {
        1: {
            "0xpoola": {"0xlp1": 0.5},
            "0xpoolb": {"0xlp1": 0.51},
        },
    }

    with pytest.raises(AssertionError) as excinfo:
        cleancase.assertAllocations(allocations)
    assert str(excinfo.value) == "LP 0xlp1 has 1.01% allocation, > 1.0%"


@enforce_types
def test_nftvols():
    poolvols = {
        1: {"0xoCeAn": {"0xpOolA": 1.0, "0xPOOLB": 2.0}, "0xH2o": {"0xPOoLC": 3.0}},
        2: {"0xocean": {"0xPOOLD": 4.0}},
    }

    target_poolvols = {
        1: {"0xocean": {"0xpoola": 1.0, "0xpoolb": 2.0}, "0xh2o": {"0xpoolc": 3.0}},
        2: {"0xocean": {"0xpoold": 4.0}},
    }

    with pytest.raises(AssertionError):
        cleancase.assertNFTvols(poolvols)

    mod_poolvols = cleancase.modNFTvols(poolvols)
    cleancase.assertNFTvols(mod_poolvols)
    assert mod_poolvols == target_poolvols


@enforce_types
def test_rates_main():
    rates = {"oCeAn": 0.25, "h2o": 1.61}
    target_rates = {"OCEAN": 0.25, "H2O": 1.61}

    with pytest.raises(AssertionError):
        cleancase.assertRates(rates)

    mod_rates = cleancase.modRates(rates)
    cleancase.assertRates(mod_rates)
    assert mod_rates == target_rates


@enforce_types
def test_rates_0x():
    rates = {"0xOCEAN": 0.1}
    with pytest.raises(AssertionError):
        cleancase.assertRates(rates)
