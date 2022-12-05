from enforce_typing import enforce_types
import pytest

from util import csvs


# for shorter lines
C1, C2 = 1, 137
PA, PB, PC, PD, PE, PF = "0xpa", "0xpb", "0xpc", "0xpd", "0xpe", "0xpf"  # nfts
LP1, LP2, LP3, LP4, LP5, LP6 = "0xlp1", "0xlp2", "0xlp3", "0xlp4", "0xlp5", "0xlp6"
OCN_SYMB, H2O_SYMB = "OCN", "H2O"
OCN_ADDR, H2O_ADDR = "0xocn_addr", "0xh2o_addr"  # all lowercase
OCN_ADDR2, H2O_ADDR2 = "0xOCN_AdDr", "0xh2O_ADDR"  # not all lowercase


# =================================================================
# allocations csvs


@enforce_types
def test_allocations_onechain_lowercase(tmp_path):
    csv_dir = str(tmp_path)
    allocs = {
        C1: {
            PA: {LP1: 0.1, LP2: 1.0},
            PB: {LP1: 0.2, LP3: 1.0},
            PC: {LP1: 0.7, LP4: 1.0},
        }
    }
    csvs.saveAllocationCsv(allocs, csv_dir)
    allocs_loaded = csvs.loadAllocationCsvs(csv_dir)
    assert allocs_loaded == allocs


@enforce_types
def test_allocations_onechain_mixedcase(tmp_path):
    csv_dir = str(tmp_path)
    allocs_lowercase = {
        C1: {
            PA: {"0xlp1": 0.1, "0xlp2": 1.0},
            PB: {"0xlp1": 0.2, "0xlp3": 1.0},
            PC: {"0xlp1": 0.7, "0xlp4": 1.0},
        }
    }
    allocs_mixedcase = {
        C1: {
            PA: {"0xlP1": 0.1, "0xLP2": 1.0},
            PB: {"0xLp1": 0.2, "0xlp3": 1.0},
            PC: {"0xlp1": 0.7, "0xLp4": 1.0},
        }
    }
    csvs.saveAllocationCsv(allocs_mixedcase, csv_dir)
    allocs_loaded = csvs.loadAllocationCsvs(csv_dir)
    assert allocs_loaded == allocs_lowercase


@enforce_types
def test_allocations_twochains(tmp_path):
    csv_dir = str(tmp_path)
    allocs = {
        C1: {
            PA: {LP1: 0.1, LP2: 1.0},
            PB: {LP1: 0.3, LP3: 1.0},
            PC: {LP1: 0.5, LP4: 1.0},
        },
        C2: {PD: {LP1: 0.1, LP5: 1.0}, PE: {LP6: 1.0}},
    }

    csvs.saveAllocationCsv(allocs, csv_dir)
    allocs_loaded = csvs.loadAllocationCsvs(csv_dir)
    assert allocs_loaded == allocs


# =================================================================
# vebals csvs


@enforce_types
def test_vebals(tmp_path):
    csv_dir = str(tmp_path)

    vebals = {LP1: 1.0, LP2: 2.0, LP3: 3.0}
    locked_amt = {LP1: 10.0, LP2: 20.0, LP3: 3.0}
    unlock_time = {LP1: 1, LP2: 1, LP3: 3}
    csvs.saveVebalsCsv(vebals, locked_amt, unlock_time, csv_dir)
    loaded_vebals, locked_amts, unlock_times = csvs.loadVebalsCsv(csv_dir)
    assert loaded_vebals == vebals
    assert locked_amts == locked_amt
    assert unlock_times == unlock_time


# =================================================================
# nftvols csvs


@enforce_types
def test_chainIDforNftvolsCsv():
    assert csvs.chainIDforNftvolsCsv("poolvols-chain101.csv") == 101
    assert csvs.chainIDforNftvolsCsv("path1/32/poolvols-chain92.csv") == 92


@enforce_types
def test_nftvols_onechain_lowercase(tmp_path):
    csv_dir = str(tmp_path)
    V1 = {OCN_ADDR: {PA: 1.1, PB: 2.1}, H2O_ADDR: {PC: 3.1}}
    csvs.saveNftvolsCsv(V1, csv_dir, C1)
    V1_loaded = csvs.loadNftvolsCsv(csv_dir, C1)
    assert V1_loaded == V1


@enforce_types
def test_nftvols_onechain_mixedcase(tmp_path):
    csv_dir = str(tmp_path)
    V1_lowercase = {OCN_ADDR: {PA: 1.1, PB: 2.1}, H2O_ADDR: {PC: 3.1}}
    V1_mixedcase = {OCN_ADDR2: {PA: 1.1, PB: 2.1}, H2O_ADDR2: {PC: 3.1}}
    csvs.saveNftvolsCsv(V1_mixedcase, csv_dir, C1)
    V1_loaded = csvs.loadNftvolsCsv(csv_dir, C1)
    assert V1_loaded == V1_lowercase


@enforce_types
def test_nftvols_twochains(tmp_path):
    csv_dir = str(tmp_path)
    V1 = {OCN_ADDR: {PA: 1.1, PB: 2.1}, H2O_ADDR: {PC: 3.1}}
    V2 = {OCN_ADDR: {PD: 4.1, PE: 5.1}, H2O_ADDR: {PF: 6.1}}

    assert len(csvs.nftvolsCsvFilenames(csv_dir)) == 0
    csvs.saveNftvolsCsv(V1, csv_dir, C1)
    csvs.saveNftvolsCsv(V2, csv_dir, C2)
    assert len(csvs.nftvolsCsvFilenames(csv_dir)) == 2

    target_V = {C1: V1, C2: V2}
    loaded_V = csvs.loadNftvolsCsvs(csv_dir)
    assert loaded_V == target_V


# =================================================================
# approved csvs


@enforce_types
def test_chainIDforApprovedCsv():
    assert csvs.chainIDforApprovedCsv("approved-chain101.csv") == 101
    assert csvs.chainIDforApprovedCsv("path1/32/approved-chain92.csv") == 92


@enforce_types
def test_approved(tmp_path):
    csv_dir = str(tmp_path)

    approved_C1 = ["0x123", "0x456"]
    approved_C2 = ["0x789"]

    csvs.saveApprovedCsv(approved_C1, csv_dir, C1)
    csvs.saveApprovedCsv(approved_C2, csv_dir, C2)

    loaded_approved_C1 = csvs.loadApprovedCsv(csv_dir, C1)
    loaded_approved_C2 = csvs.loadApprovedCsv(csv_dir, C2)
    loaded_approved = csvs.loadApprovedCsvs(csv_dir)

    assert loaded_approved_C1 == approved_C1
    assert loaded_approved_C2 == approved_C2
    assert loaded_approved == {C1: approved_C1, C2: approved_C2}


# =================================================================
# symbols csvs


@enforce_types
def test_chainIDforSymbolsCsv():
    assert csvs.chainIDforSymbolsCsv("symbols-chain101.csv") == 101
    assert csvs.chainIDforSymbolsCsv("path1/32/symbols-chain92.csv") == 92


@enforce_types
def test_symbols(tmp_path):
    csv_dir = str(tmp_path)

    symbols_C1 = {"0x123": "OCEAN", "0x456": "H2O"}
    symbols_C2 = {"0x789": "MOCEAN", "0xabc": "H2O"}

    csvs.saveSymbolsCsv(symbols_C1, csv_dir, C1)
    csvs.saveSymbolsCsv(symbols_C2, csv_dir, C2)

    loaded_symbols_C1 = csvs.loadSymbolsCsv(csv_dir, C1)
    loaded_symbols_C2 = csvs.loadSymbolsCsv(csv_dir, C2)
    loaded_symbols = csvs.loadSymbolsCsvs(csv_dir)

    assert loaded_symbols_C1 == symbols_C1
    assert loaded_symbols_C2 == symbols_C2
    assert loaded_symbols == {C1: symbols_C1, C2: symbols_C2}


# =================================================================
# exchange rate csvs


@enforce_types
def test_rates(tmp_path):
    rates = {OCN_SYMB: 0.66, H2O_SYMB: 1.618}

    csv_dir = str(tmp_path)
    assert len(csvs.rateCsvFilenames(csv_dir)) == 0
    csvs.saveRateCsv(OCN_SYMB, rates[OCN_SYMB], csv_dir)
    assert len(csvs.rateCsvFilenames(csv_dir)) == 1
    csvs.saveRateCsv(H2O_SYMB, rates[H2O_SYMB], csv_dir)
    assert len(csvs.rateCsvFilenames(csv_dir)) == 2

    loaded_rates = csvs.loadRateCsvs(csv_dir)
    assert loaded_rates == rates


# ========================================================================
# rewardsperlp csvs


@enforce_types
def test_rewardsperlp_filename(tmp_path):
    csv_dir = str(tmp_path)
    fname = csvs.rewardsperlpCsvFilename(csv_dir, "MYTOKEN")
    target_fname = csv_dir + "/" + "rewardsperlp-MYTOKEN.csv"
    assert fname == target_fname


@enforce_types
def test_rewardsperlp_main(tmp_path):
    rewards = {1: {LP1: 1.1, LP2: 2.2, LP3: 3.3}, 137: {LP1: 137.1, LP3: 137.3}}
    target_rewards = rewards

    csv_dir = str(tmp_path)
    csvs.saveRewardsperlpCsv(rewards, csv_dir, "MYTOKEN")

    loaded_rewards = csvs.loadRewardsCsv(csv_dir, "MYTOKEN")
    assert loaded_rewards == target_rewards

    for innerdict in rewards.values():  # ensures we don't deal in weis
        for value in innerdict.values():
            assert isinstance(value, float)


# ========================================================================
# rewardsinfo csvs


@enforce_types
def test_rewardsinfo(
    tmp_path, network_setup_and_teardown
):  # pylint: disable=unused-argument
    rewards = {
        1: {
            PA: {LP1: 3.2, LP2: 5.4},
            PB: {
                LP2: 5.3,
                LP3: 6.234262346,
                LP3: 1.324824324234,
            },
            PC: {LP3: 1.324824324234, LP4: 1.23143252346354},
        },
        137: {
            PD: {LP1: 1412341242, LP2: 23424},
            PE: {LP1: 0.000000000000001, LP2: 12314552354},
        },
    }
    target_rewards = """chainID,nft_addr,LP_addr,amt,token
1,0xpa,0xlp1,3.2,MYTOKEN
1,0xpa,0xlp2,5.4,MYTOKEN
1,0xpb,0xlp2,5.3,MYTOKEN
1,0xpb,0xlp3,1.324824324234,MYTOKEN
1,0xpc,0xlp3,1.324824324234,MYTOKEN
1,0xpc,0xlp4,1.23143252346354,MYTOKEN
137,0xpd,0xlp1,1412341242,MYTOKEN
137,0xpd,0xlp2,23424,MYTOKEN
137,0xpe,0xlp1,1e-15,MYTOKEN
137,0xpe,0xlp2,12314552354,MYTOKEN
"""

    csv_dir = str(tmp_path)
    csvs.saveRewardsinfoCsv(rewards, csv_dir, "MYTOKEN")

    # pylint: disable=consider-using-with
    loaded_rewards = open(csvs.rewardsinfoCsvFilename(csv_dir, "MYTOKEN"), "r")
    csv = loaded_rewards.read()
    assert csv == target_rewards


# =================================================================
# helper funcs
@enforce_types
def test_assertIsEthAddr():
    csvs.assertIsEthAddr("0xFOO")
    csvs.assertIsEthAddr("0x967da4048cd07ab37855c090aaf366e4ce1b9f48")
    with pytest.raises(AssertionError):
        csvs.assertIsEthAddr("FOO")


# =================================================================
