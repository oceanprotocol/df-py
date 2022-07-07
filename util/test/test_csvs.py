import os

import brownie
from enforce_typing import enforce_types
import pandas as pd

from util import csvs, networkutil, query
from util.query import SimplePool
from util.tok import TokSet


accounts = None

# for shorter lines
C1, C2 = 1, 137
PA, PB, PC, PD, PE, PF = (
    "0xpoola",
    "0xpoolb",
    "0xpoolc",
    "0xpoold",
    "0xpoole",
    "0xpoolf",
)
LP1, LP2, LP3, LP4, LP5, LP6 = "0xlp1", "0xlp2", "0xlp3", "0xlp4", "0xlp5", "0xlp6"
OCN_SYMB, H2O_SYMB = "OCN", "H2O"
OCN_ADDR, H2O_ADDR = "0xOCN_addr", "0xH2O_addr"


# =================================================================
# stakes csvs


@enforce_types
def test_chainIDforStakeCsv():
    assert csvs.chainIDforStakeCsv("stakes-chain101.csv") == 101
    assert csvs.chainIDforStakeCsv("path1/32/stakes-chain92.csv") == 92


@enforce_types
def test_stakes_onechain(tmp_path):
    csv_dir = str(tmp_path)
    S1 = {
        OCN_SYMB: {PA: {LP1: 1.1, LP2: 1.2}, PB: {LP1: 2.1, LP3: 2.3}},
        H2O_SYMB: {PC: {LP1: 3.1, LP4: 3.4}},
    }
    csvs.saveStakesCsv(S1, csv_dir, C1)
    target_S1 = S1
    loaded_S1 = csvs.loadStakesCsv(csv_dir, C1)
    assert loaded_S1 == target_S1


@enforce_types
def test_stakes_twochains(tmp_path):
    csv_dir = str(tmp_path)
    S1 = {
        OCN_SYMB: {PA: {LP1: 1.1, LP2: 1.2}, PB: {LP1: 2.1, LP3: 2.3}},
        H2O_SYMB: {PC: {LP1: 3.1, LP4: 3.4}},
    }
    S2 = {OCN_SYMB: {PD: {LP1: 4.1, LP5: 4.5}}, H2O_SYMB: {PE: {LP6: 5.6}}}

    assert len(csvs.stakesCsvFilenames(csv_dir)) == 0
    csvs.saveStakesCsv(S1, csv_dir, C1)
    csvs.saveStakesCsv(S2, csv_dir, C2)
    assert len(csvs.stakesCsvFilenames(csv_dir)) == 2

    target_S = {C1: S1, C2: S2}
    loaded_S = csvs.loadStakesCsvs(csv_dir)
    assert loaded_S == target_S


# =================================================================
# poolvols csvs


@enforce_types
def test_chainIDforPoolvolsCsv():
    assert csvs.chainIDforPoolvolsCsv("poolvols-chain101.csv") == 101
    assert csvs.chainIDforPoolvolsCsv("path1/32/poolvols-chain92.csv") == 92


@enforce_types
def test_poolvols_onechain(tmp_path):
    csv_dir = str(tmp_path)
    V1 = {OCN_SYMB: {PA: 1.1, PB: 2.1}, H2O_SYMB: {PC: 3.1}}
    csvs.savePoolvolsCsv(V1, csv_dir, C1)

    target_V1 = V1
    loaded_V1 = csvs.loadPoolvolsCsv(csv_dir, C1)
    assert loaded_V1 == target_V1


@enforce_types
def test_poolvols_twochains(tmp_path):
    csv_dir = str(tmp_path)
    V1 = {OCN_SYMB: {PA: 1.1, PB: 2.1}, H2O_SYMB: {PC: 3.1}}
    V2 = {OCN_SYMB: {PD: 4.1, PE: 5.1}, H2O_SYMB: {PF: 6.1}}

    assert len(csvs.poolvolsCsvFilenames(csv_dir)) == 0
    csvs.savePoolvolsCsv(V1, csv_dir, C1)
    csvs.savePoolvolsCsv(V2, csv_dir, C2)
    assert len(csvs.poolvolsCsvFilenames(csv_dir)) == 2

    target_V = {C1: V1, C2: V2}
    loaded_V = csvs.loadPoolvolsCsvs(csv_dir)
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

    # set the data
    l1 = [(C1, "0x123", "OCEAN"), (C1, "0x456", "H2O_SYMB")]
    l2 = [(C2, "0x789", "OCEAN")]
    approved1 = TokSet(l1)
    approved2 = TokSet(l2)
    approved_all = TokSet(l1 + l2)

    # test on just chain1
    csvs.saveApprovedCsv(approved1, csv_dir, C1)
    loaded1 = csvs.loadApprovedCsv(csv_dir, C1)
    assert loaded1.hasChain(C1)
    assert loaded1.hasAddress(C1, "0x123")
    assert loaded1.hasAddress(C1, "0x456")

    filename = csvs.approvedCsvFilename(csv_dir, C1)
    os.remove(filename)

    csvs.saveApprovedCsv(approved_all, csv_dir, C1)  # should only save C1
    loaded_all = csvs.loadApprovedCsvs(csv_dir)
    assert loaded_all.hasChain(C1)
    assert not loaded_all.hasChain(C2)

    # test on just chain2
    csvs.saveApprovedCsv(approved2, csv_dir, C2)
    loaded2 = csvs.loadApprovedCsv(csv_dir, C2)
    assert loaded2.hasAddress(C2, "0x789")

    # test on both chains
    loaded1 = csvs.loadApprovedCsv(csv_dir, C1)
    assert loaded1.hasChain(C1)
    assert not loaded1.hasChain(C2)  # should have filtered out C2

    loaded2 = csvs.loadApprovedCsv(csv_dir, C2)
    assert loaded2.hasChain(C2)
    assert not loaded2.hasChain(C1)  # should have filtered out C1

    loaded_all = csvs.loadApprovedCsvs(csv_dir)
    assert loaded_all.hasChain(C1)
    assert loaded_all.hasChain(C2)


# =================================================================
# poolinfo csvs


@enforce_types
def test_poolinfo(tmp_path):
    csv_dir = str(tmp_path)
    nft1_addr, nft2_addr, nft3_addr = (
        accounts[5].address,
        accounts[6].address,
        accounts[7].address,
    )
    P1 = [
        SimplePool(PA, nft1_addr, "dt1_addr", "DT1_SYM", OCN_ADDR),
        SimplePool(PB, nft2_addr, "dt2_addr", "DT2_SYM", H2O_ADDR),
        SimplePool(PC, nft3_addr, "dt3_addr", "DT3_SYM", OCN_ADDR),
    ]
    S1 = {
        OCN_SYMB: {PA: {LP1: 1.1, LP2: 1.2}, PB: {LP1: 2.1, LP3: 2.3}},
        H2O_SYMB: {PC: {LP1: 3.1, LP4: 3.4}},
    }
    V1 = {OCN_SYMB: {PA: 0.11, PB: 0.12}, H2O_SYMB: {PC: 3.1}}

    rates = {OCN_SYMB: 0.66, H2O_SYMB: 1.618}
    for symbol, rate in rates.items():
        csvs.saveRateCsv(symbol, rate, csv_dir)

    query._ADDR_TO_SYMBOL[
        OCN_ADDR
    ] = OCN_SYMB  # to make call to query.symbol(OCN_ADDR) happy
    query._ADDR_TO_SYMBOL[H2O_ADDR] = H2O_SYMB  # .. H2O_ADDR ..

    csvs.savePoolinfoCsv(P1, S1, V1, csv_dir, C1)

    csv_file = csvs.poolinfoCsvFilename(csv_dir, C1)

    target_header = [
        "chainID",
        "basetoken",
        "pool_addr",
        "vol_amt",
        "vol_amt_USD",
        "stake_amt",
        "stake_amt_USD",
        "nft_addr",
        "DT_addr",
        "DT_symbol",
        "basetoken_addr",
        "did",
        "url",
    ]

    data = pd.read_csv(csv_file)
    header = list(data.columns)
    assert header == target_header

    # (skip fancier tests)


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
# rewards csvs


@enforce_types
def test_rewards_filename(tmp_path):
    csv_dir = str(tmp_path)
    fname = csvs.rewardsperlpCsvFilename(csv_dir, "MYTOKEN")
    target_fname = csv_dir + "/" + "rewardsperlp-MYTOKEN.csv"
    assert fname == target_fname


@enforce_types
def test_rewards_main(tmp_path):
    rewards = {1: {LP1: 1.1, LP2: 2.2, LP3: 3.3}, 137: {LP1: 137.1, LP3: 137.3}}
    target_rewards = rewards

    csv_dir = str(tmp_path)
    csvs.saveRewardsperlpCsv(rewards, csv_dir, "MYTOKEN")

    loaded_rewards = csvs.loadRewardsCsv(csv_dir, "MYTOKEN")
    assert loaded_rewards == target_rewards

    for innerdict in rewards.values():  # ensures we don't deal in weis
        for value in innerdict.values():
            assert isinstance(value, float)


@enforce_types
def test_rewards_info(tmp_path):
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
    target_rewards = """chainID,pool_addr,LP_addr,amt,token
1,0xpoola,0xlp1,3.2,MYTOKEN
1,0xpoola,0xlp2,5.4,MYTOKEN
1,0xpoolb,0xlp2,5.3,MYTOKEN
1,0xpoolb,0xlp3,1.324824324234,MYTOKEN
1,0xpoolc,0xlp3,1.324824324234,MYTOKEN
1,0xpoolc,0xlp4,1.23143252346354,MYTOKEN
137,0xpoold,0xlp1,1412341242,MYTOKEN
137,0xpoold,0xlp2,23424,MYTOKEN
137,0xpoole,0xlp1,1e-15,MYTOKEN
137,0xpoole,0xlp2,12314552354,MYTOKEN
"""

    csv_dir = str(tmp_path)
    csvs.saveRewardsinfoCsv(rewards, csv_dir, "MYTOKEN")

    # pylint: disable=consider-using-with
    loaded_rewards = open(csvs.rewardsinfoCsvFilename(csv_dir, "MYTOKEN"), "r")
    csv = loaded_rewards.read()
    assert csv == target_rewards


@enforce_types
def setup_function():
    networkutil.connect(networkutil.DEV_CHAINID)
    global accounts
    accounts = brownie.network.accounts


@enforce_types
def teardown_function():
    networkutil.disconnect()
