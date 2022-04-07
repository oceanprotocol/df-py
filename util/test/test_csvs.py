from enforce_typing import enforce_types

from util import csvs

@enforce_types
def test_stakes(tmp_path):
    stakes_chain1 = {"OCEAN": {"pool1": {"LP1": 1.1, "LP1": 1.2},
                               "pool2": {"LP1": 2.1, "LP3": 2.3}},
                     "H2O"  : {"pool3": {"LP1": 3.1, "LP4": 3.4}}}
                               
    stakes_chain2 = {"OCEAN": {"pool4": {"LP1": 4.1, "LP5": 4.5}},
                     "H2O"  : {"pool5": {"LP6": 5.6}}}

    #target is a merging of the above dicts
    target_stakes = {"OCEAN": {"pool1": {"LP1": 1.1, "LP1": 1.2},
                               "pool2": {"LP1": 2.1, "LP3": 2.3},
                               "pool4": {"LP1": 4.1, "LP5": 4.5}},
                     "H2O"  : {"pool3": {"LP1": 3.1, "LP4": 3.4},
                               "pool5": {"LP6": 5.6}}}
    
    csv_dir = str(tmp_path)
    assert len(csvs.stakesCsvFilenames(csv_dir)) == 0
    csvs.saveStakesCsv(stakes_chain1, csv_dir, "chain1")
    assert len(csvs.stakesCsvFilenames(csv_dir)) == 1
    csvs.saveStakesCsv(stakes_chain2, csv_dir, "chain2")
    assert len(csvs.stakesCsvFilenames(csv_dir)) == 2

    loaded_stakes = csvs.loadStakesCsvs(csv_dir)    
    assert loaded_stakes == target_stakes

@enforce_types
def test_poolVols(tmp_path):
    pool_vols_chain1 = {"OCEAN": {"pool1":1.1, "pool2":2.1},
                        "H2O"  : {"pool3":3.1}}
    pool_vols_chain2 = {"OCEAN": {"pool4":4.1, "pool5":5.1},
                        "H2O"  : {"pool6":6.1}}

    #target is a merging of the above dicts
    target_pool_vols = {"OCEAN": {"pool1":1.1, "pool2":2.1,
                                  "pool4":4.1, "pool5":5.1},
                        "H2O"  : {"pool3":3.1, "pool6":6.1}}
        
    csv_dir = str(tmp_path)
    assert len(csvs.poolVolsCsvFilenames(csv_dir)) == 0
    csvs.savePoolVolsCsv(pool_vols_chain1, csv_dir, "chain1")
    assert len(csvs.poolVolsCsvFilenames(csv_dir)) == 1
    csvs.savePoolVolsCsv(pool_vols_chain2, csv_dir, "chain2")
    assert len(csvs.poolVolsCsvFilenames(csv_dir)) == 2
    
    loaded_pool_vols = csvs.loadPoolVolsCsvs(csv_dir)
    assert loaded_pool_vols == target_pool_vols

@enforce_types
def test_rates(tmp_path):
    rates = {"OCEAN" : 0.66, "H2O" : 1.618}
        
    csv_dir = str(tmp_path)
    assert len(csvs.rateCsvFilenames(csv_dir)) == 0
    csvs.saveRateCsv("OCEAN", rates["OCEAN"], csv_dir)
    assert len(csvs.rateCsvFilenames(csv_dir)) == 1
    csvs.saveRateCsv("H2O", rates["H2O"], csv_dir)
    assert len(csvs.rateCsvFilenames(csv_dir)) == 2
    
    loaded_rates = csvs.loadRateCsvs(csv_dir)
    assert loaded_rates == rates

@enforce_types
def test_rewards(tmp_path):
    rewards = {"LP1":1.1, "LP2":2.2, "LP3":3.0}
    target_rewards = rewards
    
    csv_dir = str(tmp_path)
    csvs.saveRewardsCsv(rewards, csv_dir)
        
    loaded_rewards = csvs.loadRewardsCsv(csv_dir)
    assert loaded_rewards == target_rewards

    for value in rewards.values(): #ensures we don't deal in weis
        assert type(value) == float
