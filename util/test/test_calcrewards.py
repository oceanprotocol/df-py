from enforce_typing import enforce_types
import pytest

from util.calcrewards import calcRewards, _stakesToUsd, _poolvolsToUsd

RATES = {"ocean": 0.5, "h2o": 1.6}

#for shorter lines
C1, C2 = "chain1", "chain2"
PA, PB, PC = "poolA", "poolB", "poolC"
LP1, LP2, LP3, LP4 = "LP1", "LP2", "LP3", "LP4"
OCN, H2O = "ocean", "h2o"

@enforce_types
def test_calcRewards1_onechain():
    stakes = {C1: {OCN: {PA: {LP1: 1.0}}}}
    poolvols = {C1: {OCN: {PA: 1.0}}}
    rewards = calcRewards(stakes, poolvols, RATES, OCEAN_avail=10.0)
    assert rewards == {C1: {LP1: 10.0}}

    
@enforce_types
def test_calcRewards1_twochains():
    stakes = {C1: {OCN: {PA: {LP1: 1.0}}},
              C2: {OCN: {PB: {LP1: 1.0}}}}
    poolvols = {C1: {OCN: {PA: 1.0}},
                 C2: {OCN: {PB: 1.0}}}
    rewards = calcRewards(stakes, poolvols, RATES, OCEAN_avail=20.0)
    assert rewards == {C1: {LP1: 10.0}, C2: {LP1: 10.0}}


@enforce_types
def test_calcRewards2():
    stakes = {C1: {OCN: {PA: {LP1: 1.0, LP2: 1.0}}}}
    poolvols = {C1: {OCN: {PA: 1.0}}}
    rewards = calcRewards(stakes, poolvols, RATES, OCEAN_avail=10.0)
    assert sum(rewards[C1].values()) == pytest.approx(10.0, 0.01)
    assert rewards == {C1: {LP1: 5.0, LP2: 5.0}}


@enforce_types
def test_calcRewards3():
    stakes = {C1: {OCN: {PA: {LP1: 1.0, LP2: 1.0}, PB: {LP1: 1.0, LP3: 1.0}}}}
    poolvols = {C1: {OCN: {PA: 1.0}}}  # P1 has volume, but not P2
    rewards = calcRewards(stakes, poolvols, RATES, OCEAN_avail=10.0)
    assert sum(rewards[C1].values()) == pytest.approx(10.0, 0.01)
    assert min(rewards[C1].values()) > 0,"shouldn't have entries with 0 rewards"
    assert rewards == {C1: {LP1: 5.0, LP2: 5.0}}


@enforce_types
def test_calcRewards4():
    stakes = {C1: {OCN: {PA: {LP1: 1.0, LP2: 1.0}, PB: {LP1: 1.0, LP3: 1.0}}}}
    poolvols = {C1: {OCN: {PA: 1.0, PB: 1.0}}}  # P1 & P2 both have volume
    rewards = calcRewards(stakes, poolvols, RATES, OCEAN_avail=10.0)
    assert sum(rewards[C1].values()) == pytest.approx(10.0, 0.01)
    assert rewards == {C1: {LP1: 5.0, LP2: 2.5, LP3: 2.5}}


@enforce_types
def test_stakesToUsd_onebasetoken():
    stakes = {C1: {OCN: {PA: {LP1: 3.0, LP2: 4.0}}}}
    stakes_USD = _stakesToUsd(stakes, RATES)
    assert stakes_USD == {C1: {PA: {LP1: 3.0 * 0.5, LP2: 4.0 * 0.5}}}


@enforce_types
def test_stakesToUsd_twobasetokens():
    stakes = {C1: {
        OCN: {PA: {LP1: 3.0, LP2: 4.0}},
        H2O: {PC: {LP1: 5.0, LP4: 6.0}},
    }}
    stakes_USD = _stakesToUsd(stakes, RATES)
    assert stakes_USD == {C1: {
        PA: {LP1: 3.0 * 0.5, LP2: 4.0 * 0.5},
        PC: {LP1: 5.0 * 1.6, LP4: 6.0 * 1.6},
    }}


@enforce_types
def test_poolvolsToUsd_onebasetoken():
    poolvols = {C1: {OCN: {PA: 9.0, PB: 11.0}}}
    poolvols_USD = _poolvolsToUsd(poolvols, RATES)
    assert poolvols_USD == {C1: {PA: 9.0 * 0.5, PB: 11.0 * 0.5}}


@enforce_types
def test_poolvolsToUsd_twobasetokens():
    poolvols = {C1: {OCN: {PA: 9.0, PB: 11.0}, H2O: {PC: 13.0}}}
    poolvols_USD = _poolvolsToUsd(poolvols, RATES)
    assert poolvols_USD == {C1: {
        PA: 9.0 * 0.5,
        PB: 11.0 * 0.5,
        PC: 13.0 * 1.6,
    }}
