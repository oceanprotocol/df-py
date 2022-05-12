from enforce_typing import enforce_types

from util import csvs

#for shorter lines
C1, C2 = "chain1", "chain2"
PA, PB, PC, PD, PE, PF = "poolA", "poolB", "poolC", "poolD", "poolE", "poolF"
LP1, LP2, LP3, LP4, LP5, LP6 = "LP1", "LP2", "LP3", "LP4", "LP5", "LP6"
OCN, H2O = "OCEAN", "H2O"

@enforce_types
def test_stakes(tmp_path):
    stakes_chain1 = {
        OCN: {PA: {LP1: 1.1, LP1: 1.2}, PB: {LP1: 2.1, LP3: 2.3}},
        H2O: {PC: {LP1: 3.1, LP4: 3.4}},
    }

    stakes_chain2 = {
        OCN: {PD: {LP1: 4.1, LP5: 4.5}},
        H2O: {PE: {LP6: 5.6}},
    }

    # target is a merging of the above dicts
    target_stakes = {
        OCN: {
            PA: {LP1: 1.1, LP1: 1.2},
            PB: {LP1: 2.1, LP3: 2.3},
            PD: {LP1: 4.1, LP5: 4.5},
        },
        H2O: {PC: {LP1: 3.1, LP4: 3.4}, PE: {LP6: 5.6}},
    }

    csv_dir = str(tmp_path)
    assert len(csvs.stakesCsvFilenames(csv_dir)) == 0
    csvs.saveStakesCsv(stakes_chain1, csv_dir, C1)
    assert len(csvs.stakesCsvFilenames(csv_dir)) == 1
    csvs.saveStakesCsv(stakes_chain2, csv_dir, C2)
    assert len(csvs.stakesCsvFilenames(csv_dir)) == 2

    loaded_stakes = csvs.loadStakesCsvs(csv_dir)
    assert loaded_stakes == target_stakes


@enforce_types
def test_poolVols(tmp_path):
    pool_vols_chain1 = {OCN: {PA: 1.1, PB: 2.1}, H2O: {PC: 3.1}}
    pool_vols_chain2 = {OCN: {PD: 4.1, PE: 5.1}, H2O: {PF: 6.1}}

    # target is a merging of the above dicts
    target_pool_vols = {
        OCN: {PA: 1.1, PB: 2.1, PD: 4.1, PE: 5.1},
        H2O: {PC: 3.1, PF: 6.1},
    }

    csv_dir = str(tmp_path)
    assert len(csvs.poolVolsCsvFilenames(csv_dir)) == 0
    csvs.savePoolVolsCsv(pool_vols_chain1, csv_dir, C1)
    assert len(csvs.poolVolsCsvFilenames(csv_dir)) == 1
    csvs.savePoolVolsCsv(pool_vols_chain2, csv_dir, C2)
    assert len(csvs.poolVolsCsvFilenames(csv_dir)) == 2

    loaded_pool_vols = csvs.loadPoolVolsCsvs(csv_dir)
    assert loaded_pool_vols == target_pool_vols


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
