from enforce_typing import enforce_types

from util import csvs
from util.allocations import allocsToStakes, loadStakes

# for shorter lines
C1, C2 = 7, 137
NA, NB = "0xnfta_addr", "0xnftb_addr"
ST1, ST2, ST3 = "0xst1_addr", "0xst2_addr", "0xst3_addr"


@enforce_types
def test_empty():
    assert allocsToStakes({}, {}) == {}
    assert allocsToStakes({C1: {}}, {}) == {C1: {}}
    assert allocsToStakes({C1: {NA: {}}}, {}) == {C1: {NA: {}}}
    assert allocsToStakes({C1: {NA: {ST1: 1.0}}}, {}) == {C1: {NA: {ST1: 0.0}}}
    assert allocsToStakes({C1: {NA: {}}}, {ST1: 5.0}) == {C1: {NA: {}}}


@enforce_types
def test_lp1_one_allocation():
    perc_allocs = {C1: {NA: {ST1: 1.0}}}
    vebals = {ST1: 10.0}
    stakes = allocsToStakes(perc_allocs, vebals)
    assert stakes == {C1: {NA: {ST1: 10.0}}}


@enforce_types
def test_lp1_two_allocations():
    perc_allocs = {C1: {NA: {ST1: 0.1}, NB: {ST1: 0.9}}}
    vebals = {ST1: 10.0}
    stakes = allocsToStakes(perc_allocs, vebals)
    assert stakes == {C1: {NA: {ST1: 1.0}, NB: {ST1: 9.0}}}


@enforce_types
def test_lp1_two_allocations__lp2_two_allocations():
    perc_allocs = {C1: {NA: {ST1: 0.1, ST2: 0.2}, NB: {ST1: 0.9, ST2: 0.8}}}
    vebals = {ST1: 10.0, ST2: 100.0}
    stakes = allocsToStakes(perc_allocs, vebals)
    assert stakes == {
        C1: {NA: {ST1: 1.0, ST2: 0.2 * 100}, NB: {ST1: 9.0, ST2: 0.8 * 100}}
    }


@enforce_types
def test_load_stakes(tmp_path):
    csv_dir = str(tmp_path)

    allocs = {C1: {NA: {ST1: 0.1, ST2: 1.0}, NB: {ST1: 0.2}}}
    csvs.saveAllocationCsv(allocs, csv_dir)

    vebals = {ST1: 100.0, ST2: 200.0}
    locked_amt = {ST1: 10.0, ST2: 20.0}
    unlock_time = {ST1: 1, ST2: 1}
    csvs.saveVebalsCsv(vebals, locked_amt, unlock_time, csv_dir)

    target_stakes = allocsToStakes(allocs, vebals)
    loaded_stakes = loadStakes(csv_dir)
    assert loaded_stakes == target_stakes
