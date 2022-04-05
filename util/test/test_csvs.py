from enforce_typing import enforce_types

from util import csvs

@enforce_types
def test_stakes(tmp_path):
    stakes_chain1 = {"pool1": {"LP1": 1.1, "LP2": 2.2},
                     "pool2": {"LP1": 3.3, "LP3": 4.4}}
    stakes_chain2 = {"pool3": {"LP1": 5.5, "LP4": 6.6}}
    target_stakes = {**stakes_chain1, **stakes_chain2} #merge two dicts

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
    pool_vols_chain1 = {"pool1":1.1, "pool2":2.2}
    pool_vols_chain2 = {"pool3":3.3}
    target_pool_vols = {**pool_vols_chain1, **pool_vols_chain2} #merge two dicts
    
    csv_dir = str(tmp_path)
    assert len(csvs.poolVolsCsvFilenames(csv_dir)) == 0
    csvs.savePoolVolsCsv(pool_vols_chain1, csv_dir, "chain1")
    assert len(csvs.poolVolsCsvFilenames(csv_dir)) == 1
    csvs.savePoolVolsCsv(pool_vols_chain2, csv_dir, "chain2")
    assert len(csvs.poolVolsCsvFilenames(csv_dir)) == 2
    
    loaded_pool_vols = csvs.loadPoolVolsCsvs(csv_dir)
    assert loaded_pool_vols == target_pool_vols

@enforce_types
def test_rewards(tmp_path):
    #tests for rewards csvs are currently in test_dispense.py
    pass
    
