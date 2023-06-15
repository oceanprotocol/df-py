from enforce_typing import enforce_types

from df_py.challenge import csvs


@enforce_types
def test_challenge_data(tmp_path):
    csv_dir = str(tmp_path)

    # filename
    assert "challenge.csv" in csvs.challenge_data_csv_filename(csv_dir)

    # save
    from_addrs = ["0xfrom1", "0xfrom2"]
    nft_addrs = ["0xnft1", "0xnft2"]
    nmses = [0.2, 1.0]
    challenge_data = (from_addrs, nft_addrs, nmses)
    csvs.save_challenge_data_csv(challenge_data, csv_dir)

    # load & compare
    challenge_data2 = csvs.load_challenge_data_csv(csv_dir)
    (from_addrs2, nft_addrs2, nmses2) = challenge_data2
    assert from_addrs2 == from_addrs
    assert nft_addrs2 == nft_addrs
    assert nmses2 == nmses


@enforce_types
def test_challenge_rewards(tmp_path):
    csv_dir = str(tmp_path)

    # filename
    assert "challenge_rewards.csv" in csvs.challenge_rewards_csv_filename(csv_dir)

    rewards = [
        {
            "winner_addr": "0xfrom1",
            "OCEAN_amt": 200,
        },
        {
            "winner_addr": "0xfrom2",
            "OCEAN_amt": 100,
        },
        {
            "winner_addr": "0xfrom3",
            "OCEAN_amt": 50,
        },
    ]

    assert csvs.save_challenge_rewards_csv(rewards, csv_dir)
    loaded_rewards = csvs.load_challenge_rewards_csv(csv_dir)
    assert loaded_rewards == rewards
