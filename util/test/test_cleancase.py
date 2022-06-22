from enforce_typing import enforce_types
import pytest

from util import cleancase


@enforce_types
def test_approvedTokens():
    approved_tokens = {"0x98aBcD3" : "OcEaN", "0xaa2BBcc": "h2O"}
    target_approved_tokens = {"0x98abcd3" : "OCEAN", "0xaa2bbcc" : "H2O"}
    with pytest.raises(AssertionError):
        cleancase.assertApprovedTokens(approved_tokens)

    mod_approved_tokens = cleancase.modApprovedTokens(approved_tokens)
    cleancase.assertApprovedTokens(mod_approved_tokens)
    assert mod_approved_tokens == target_approved_tokens


@enforce_types
def test_stakes():
    stakes = {
        1: {
            "oCeAn": {"pOolA": {"Lp1": 1.0, "LP2": 2.0}, "POOLB": {"LP3": 3.0}},
            "H2o": {"POoLC": {"lP4": 4.0}},
        },
        2: {"ocean": {"POOLD": {"LP5": 5.0}}},
    }
    target_stakes = {
        1: {
            "ocean": {"poola": {"lp1": 1.0, "lp2": 2.0}, "poolb": {"lp3": 3.0}},
            "h2o": {"poolc": {"lp4": 4.0}},
        },
        2: {"ocean": {"poold": {"lp5": 5.0}}},
    }

    with pytest.raises(AssertionError):
        cleancase.assertStakes(stakes)

    mod_stakes = cleancase.modStakes(stakes)
    cleancase.assertStakes(mod_stakes)
    assert mod_stakes == target_stakes


@enforce_types
def test_poolvols():
    poolvols = {
        1: {"oCeAn": {"pOolA": 1.0, "POOLB": 2.0}, "H2o": {"POoLC": 3.0}},
        2: {"ocean": {"POOLD": 4.0}},
    }

    target_poolvols = {
        1: {"ocean": {"poola": 1.0, "poolb": 2.0}, "h2o": {"poolc": 3.0}},
        2: {"ocean": {"poold": 4.0}},
    }

    with pytest.raises(AssertionError):
        cleancase.assertPoolvols(poolvols)

    mod_poolvols = cleancase.modPoolvols(poolvols)
    cleancase.assertPoolvols(mod_poolvols)
    assert mod_poolvols == target_poolvols


@enforce_types
def test_rates():
    rates = {"oCeAn": 0.25, "H2o": 1.61}
    target_rates = {"OCEAN": 0.25, "H2O": 1.61}

    with pytest.raises(AssertionError):
        cleancase.assertRates(rates)

    mod_rates = cleancase.modRates(rates)
    cleancase.assertRates(mod_rates)
    assert mod_rates == target_rates
