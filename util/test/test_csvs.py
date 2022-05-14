from enforce_typing import enforce_types
import pandas as pd

from util.query import SimplePool
from util import csvs

#for shorter lines
C1, C2 = 1, 137
PA, PB, PC, PD, PE, PF = "poola", "poolb", "poolc", "poold", "poole", "poolf"
LP1, LP2, LP3, LP4, LP5, LP6 = "lp1", "lp2", "lp3", "lp4", "lp5", "lp6"
OCN, H2O = "OCEAN", "H2O"


#=================================================================
# stakes csvs


@enforce_types
def test_chainIDforStakeCsv():
    assert csvs.chainIDforStakeCsv("stakes-chain101.csv") == 101
    assert csvs.chainIDforStakeCsv("path1/32/stakes-chain92.csv") == 92


@enforce_types
def test_stakes_onechain(tmp_path):
    csv_dir = str(tmp_path)
    S1 = {OCN: {PA: {LP1: 1.1, LP2: 1.2}, PB: {LP1: 2.1, LP3: 2.3}},
          H2O: {PC: {LP1: 3.1, LP4: 3.4}}}
    csvs.saveStakesCsv(S1, csv_dir, C1)
    target_S1 = S1
    loaded_S1 = csvs.loadStakesCsv(csv_dir, C1)
    assert loaded_S1 == target_S1


@enforce_types
def test_stakes_twochains(tmp_path):
    csv_dir = str(tmp_path)
    S1 = {OCN: {PA: {LP1: 1.1, LP2: 1.2}, PB: {LP1: 2.1, LP3: 2.3}},
          H2O: {PC: {LP1: 3.1, LP4: 3.4}}}
    S2 = {OCN: {PD: {LP1: 4.1, LP5: 4.5}},
          H2O: {PE: {LP6: 5.6}}}

    assert len(csvs.stakesCsvFilenames(csv_dir)) == 0    
    csvs.saveStakesCsv(S1, csv_dir, C1)
    csvs.saveStakesCsv(S2, csv_dir, C2)
    assert len(csvs.stakesCsvFilenames(csv_dir)) == 2

    target_S = {C1: S1, C2: S2}
    loaded_S = csvs.loadStakesCsvs(csv_dir)
    assert loaded_S == target_S


#=================================================================
# poolvols csvs


@enforce_types
def test_chainIDforPoolvolsCsv():
    assert csvs.chainIDforPoolvolsCsv("poolvols-chain101.csv") == 101
    assert csvs.chainIDforPoolvolsCsv("path1/32/poolvols-chain92.csv") == 92


@enforce_types
def test_poolvols_onechain(tmp_path):
    csv_dir = str(tmp_path)
    V1 = {OCN: {PA: 1.1, PB: 2.1}, H2O: {PC: 3.1}}
    csvs.savePoolvolsCsv(V1, csv_dir, C1)

    target_V1 = V1
    loaded_V1 = csvs.loadPoolvolsCsv(csv_dir, C1)
    assert loaded_V1 == target_V1


@enforce_types
def test_poolvols_twochains(tmp_path):
    csv_dir = str(tmp_path)
    V1 = {OCN: {PA: 1.1, PB: 2.1}, H2O: {PC: 3.1}}
    V2 = {OCN: {PD: 4.1, PE: 5.1}, H2O: {PF: 6.1}}

    assert len(csvs.poolvolsCsvFilenames(csv_dir)) == 0
    csvs.savePoolvolsCsv(V1, csv_dir, C1)
    csvs.savePoolvolsCsv(V2, csv_dir, C2)
    assert len(csvs.poolvolsCsvFilenames(csv_dir)) == 2

    target_V = {C1: V1, C2: V2}
    loaded_V = csvs.loadPoolvolsCsvs(csv_dir)
    assert loaded_V == target_V



#=================================================================
# poolinfo csvs


@enforce_types
def test_poolinfo(tmp_path):
    csv_dir = str(tmp_path)
    P1 = [SimplePool(PA, "nft1_addr", "dt1_addr", "ocn_addr"),
          SimplePool(PB, "nft2_addr", "dt2_addr", "h2o_addr"),
          SimplePool(PC, "nft3_addr", "dt3_addr", "ocn_addr")]
    S1 = {OCN: {PA: {LP1: 1.1, LP2: 1.2}, PB: {LP1: 2.1, LP3: 2.3}},
          H2O: {PC: {LP1: 3.1, LP4: 3.4}}}
    V1 = {OCN: {PA: 0.11, PB: 0.12},
          H2O: {PC: 3.1}}
    csvs.savePoolinfoCsv(P1, S1, V1, csv_dir, C1)

    csv_file = csvs.poolinfoCsvFilename(csv_dir, C1)
    
    target_header = ["chainID", "basetoken", "pool_addr", "vol_amt",
                     "stake_amt",
                     "nft_addr", "DT_addr", "DT_symbol", "basetoken_addr",
                     "did", "url"]
    
    df = pd.read_csv(csv_file)
    header = df.FIXME
    assert header == target_header

    #(skip fancier tests)


#=================================================================
# exchange rate csvs


@enforce_types
def test_rates(tmp_path):
    rates = {OCN: 0.66, H2O: 1.618}

    csv_dir = str(tmp_path)
    assert len(csvs.rateCsvFilenames(csv_dir)) == 0
    csvs.saveRateCsv(OCN, rates[OCN], csv_dir)
    assert len(csvs.rateCsvFilenames(csv_dir)) == 1
    csvs.saveRateCsv(H2O, rates[H2O], csv_dir)
    assert len(csvs.rateCsvFilenames(csv_dir)) == 2

    loaded_rates = csvs.loadRateCsvs(csv_dir)
    assert loaded_rates == rates


# ========================================================================
# rewards csvs


@enforce_types
def test_rewards_filename(tmp_path):
    csv_dir = str(tmp_path)
    fname = csvs.rewardsCsvFilename(csv_dir, "MYTOKEN")
    target_fname = csv_dir + '/' + "rewards-MYTOKEN.csv"
    assert fname == target_fname 


@enforce_types
def test_rewards_main(tmp_path):
    rewards = {1: {LP1: 1.1, LP2: 2.2, LP3: 3.3},
               137: {LP1: 137.1, LP3: 137.3}}
    target_rewards = rewards

    csv_dir = str(tmp_path)
    csvs.saveRewardsCsv(rewards, csv_dir, "MYTOKEN")

    loaded_rewards = csvs.loadRewardsCsv(csv_dir, "MYTOKEN")
    assert loaded_rewards == target_rewards
    
    for innerdict in rewards.values():  # ensures we don't deal in weis
        for value in innerdict.values():
            assert type(value) == float
