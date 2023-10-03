# pylint: disable=too-many-lines,too-many-statements
import argparse
import os
import sys

from enforce_typing import enforce_types
from eth_account import Account
from web3.main import Web3

from df_py.challenge import judge
from df_py.challenge.calc_rewards import calc_challenge_rewards
from df_py.challenge.csvs import (
    challenge_rewards_csv_filename,
    get_sample_challenge_data,
    get_sample_challenge_rewards,
    load_challenge_data_csv,
    load_challenge_rewards_csv,
    save_challenge_data_csv,
    save_challenge_rewards_csv,
)
from df_py.predictoor.csvs import (
    predictoor_data_csv_filename,
    save_predictoor_contracts_csv,
    save_predictoor_data_csv,
)
from df_py.predictoor.queries import query_predictoor_contracts, query_predictoors
from df_py.util import blockrange, dispense, get_rate, networkutil
from df_py.util.base18 import from_wei, to_wei
from df_py.util.blocktime import get_fin_block, get_st_fin_blocks, timestr_to_timestamp
from df_py.util.contract_base import ContractBase
from df_py.util.dftool_arguments import (
    CHAINID_EXAMPLES,
    DfStrategyArgumentParser,
    SimpleChainIdArgumentParser,
    StartFinArgumentParser,
    autocreate_path,
    block_or_valid_date,
    chain_type,
    challenge_date,
    do_help_long,
    existing_path,
    print_arguments,
    valid_date,
    valid_date_and_convert,
)
from df_py.util.multisig import send_multisig_tx
from df_py.util.networkutil import DEV_CHAINID, chain_id_to_multisig_addr
from df_py.util.oceantestutil import (
    random_consume_FREs,
    random_create_dataNFT_with_FREs,
    random_lock_and_allocate,
)
from df_py.util.oceanutil import (
    FeeDistributor,
    OCEAN_token,
    record_deployed_contracts,
    veAllocate,
)
from df_py.util.retry import retry_function
from df_py.util.vesting_schedule import (
    get_active_reward_amount_for_week_eth,
    get_active_reward_amount_for_week_eth_by_stream,
)
from df_py.volume import calc_rewards, csvs, queries
from df_py.volume.calc_rewards import calc_rewards_volume


@enforce_types
def do_volsym():
    parser = StartFinArgumentParser(
        description="Query chain, output volumes, symbols, owners",
        epilog=f"""Uses these envvars:
          \nADDRESS_FILE -- eg: export ADDRESS_FILE={networkutil.chain_id_to_address_file(chainID=DEV_CHAINID)}
          \nSECRET_SEED -- secret integer used to seed the rng
        """,
        command_name="volsym",
        csv_names="nftvols-CHAINID.csv, owners-CHAINID.csv, symbols-CHAINID.csv",
    )

    arguments = parser.parse_args()
    print_arguments(arguments)

    # extract envvars
    ADDRESS_FILE = _getAddressEnvvarOrExit()
    SECRET_SEED = _getSecretSeedOrExit()

    csv_dir, chain_id = arguments.CSV_DIR, arguments.CHAINID

    # check files, prep dir
    if not csvs.rate_csv_filenames(csv_dir):
        print("\nRates don't exist. Call 'dftool get_rate' first. Exiting.")
        sys.exit(1)

    web3 = networkutil.chain_id_to_web3(chain_id)
    record_deployed_contracts(ADDRESS_FILE, chain_id)

    # main work
    rng = blockrange.create_range(
        web3, arguments.ST, arguments.FIN, arguments.NSAMP, SECRET_SEED
    )
    (Vi, Ci, SYMi) = retry_function(
        queries.queryVolsOwnersSymbols, arguments.RETRIES, 60, rng, chain_id
    )

    csvs.save_nftvols_csv(Vi, csv_dir, chain_id)
    csvs.save_owners_csv(Ci, csv_dir, chain_id)
    csvs.save_symbols_csv(SYMi, csv_dir, chain_id)

    print("dftool volsym: Done")


# ========================================================================


@enforce_types
def do_nftinfo():
    parser = argparse.ArgumentParser(description="Query chain, output nft info csv")
    parser.add_argument("command", choices=["nftinfo"])
    parser.add_argument(
        "CSV_DIR", type=autocreate_path, help="output dir for nftinfo-CHAINID.csv, etc"
    )
    parser.add_argument("CHAINID", type=chain_type, help=CHAINID_EXAMPLES)
    parser.add_argument(
        "--FIN",
        default="latest",
        type=block_or_valid_date,
        help="last block # to calc on | YYYY-MM-DD | YYYY-MM-DD_HH:MM | latest",
        required=False,
    )

    arguments = parser.parse_args()
    print_arguments(arguments)

    # extract inputs
    csv_dir, chain_id, end_block = arguments.CSV_DIR, arguments.CHAINID, arguments.FIN

    # hardcoded values
    # -queries.queryNftinfo() can be problematic; it's only used for frontend data
    # -so retry 3 times with 10s delay by default
    RETRIES = 3
    DELAY_S = 10
    print(f"Hardcoded values:" f"\n RETRIES={RETRIES}" f"\n DELAY_S={DELAY_S}" "\n")

    web3 = networkutil.chain_id_to_web3(chain_id)

    # update ENDBLOCK
    end_block = get_fin_block(web3, end_block)
    print("Updated ENDBLOCK, new value = {end_block}")

    # main work
    nftinfo = retry_function(
        queries.queryNftinfo, RETRIES, DELAY_S, chain_id, end_block
    )
    csvs.save_nftinfo_csv(nftinfo, csv_dir, chain_id)

    print("dftool nftinfo: Done")


# ========================================================================


@enforce_types
def do_allocations():
    parser = StartFinArgumentParser(
        description="Query chain, outputs allocation csv",
        epilog="""Uses these envvars:
          \nSECRET_SEED -- secret integer used to seed the rng
        """,
        command_name="allocations",
        csv_names="allocations.csv or allocations_realtime.csv",
    )

    arguments = parser.parse_args()
    print_arguments(arguments)

    csv_dir, n_samp, chain_id = arguments.CSV_DIR, arguments.NSAMP, arguments.CHAINID

    # extract envvars
    SECRET_SEED = _getSecretSeedOrExit()

    _exitIfFileExists(csvs.allocation_csv_filename(csv_dir, n_samp > 1))

    web3 = networkutil.chain_id_to_web3(chain_id)

    # main work
    rng = blockrange.create_range(
        web3, arguments.ST, arguments.FIN, n_samp, SECRET_SEED
    )
    allocs = retry_function(
        queries.queryAllocations, arguments.RETRIES, 10, rng
    )
    csvs.save_allocation_csv(allocs, csv_dir, n_samp > 1)

    print("dftool allocations: Done")


# ========================================================================


@enforce_types
def do_vebals():
    parser = StartFinArgumentParser(
        description="Query chain, outputs veBalances csv",
        epilog="""Uses these envvars:
          \nSECRET_SEED -- secret integer used to seed the rng
        """,
        command_name="vebals",
        csv_names="vebals.csv or vebals_realtime.csv",
    )
    arguments = parser.parse_args()
    print_arguments(arguments)

    csv_dir, n_samp, chain_id = arguments.CSV_DIR, arguments.NSAMP, arguments.CHAINID

    # extract envvars
    SECRET_SEED = _getSecretSeedOrExit()

    _exitIfFileExists(csvs.vebals_csv_filename(csv_dir, n_samp > 1))

    web3 = networkutil.chain_id_to_web3(chain_id)
    rng = blockrange.create_range(
        web3, arguments.ST, arguments.FIN, n_samp, SECRET_SEED
    )

    balances, locked_amt, unlock_time = retry_function(
        queries.queryVebalances, arguments.RETRIES, 10, rng
    )
    csvs.save_vebals_csv(balances, locked_amt, unlock_time, csv_dir, n_samp > 1)

    print("dftool vebals: Done")


# ========================================================================
@enforce_types
def do_get_rate():
    parser = argparse.ArgumentParser(
        description="Get exchange rate, and output rate csv"
    )
    parser.add_argument("command", choices=["get_rate"])
    parser.add_argument(
        "TOKEN_SYMBOL",
        type=str,
        help="e.g. OCEAN, H20",
    )
    parser.add_argument(
        "ST",
        type=block_or_valid_date,
        help="start time -- YYYY-MM-DD",
    )
    parser.add_argument(
        "FIN",
        type=block_or_valid_date,
        help="end time -- YYYY-MM-DD",
    )
    parser.add_argument(
        "CSV_DIR",
        type=autocreate_path,
        help="output dir for rate-TOKEN_SYMBOL.csv, etc",
    )
    parser.add_argument(
        "--RETRIES",
        default=1,
        type=int,
        help="# times to retry failed queries",
        required=False,
    )

    arguments = parser.parse_args()
    print_arguments(arguments)

    token_symbol, csv_dir = arguments.TOKEN_SYMBOL, arguments.CSV_DIR

    # check files, prep dir
    _exitIfFileExists(csvs.rate_csv_filename(token_symbol, csv_dir))

    # main work
    rate = retry_function(
        get_rate.get_rate,
        arguments.RETRIES,
        60,
        token_symbol,
        arguments.ST,
        arguments.FIN,
    )
    print(f"rate = ${rate:.4f} / {token_symbol}")
    csvs.save_rate_csv(token_symbol, rate, csv_dir)

    print("dftool get_rate: Done")


# ========================================================================
@enforce_types
def do_challenge_data():
    # hardcoded values
    MUMBAI_CHAINID = 80001  # only on mumbai
    parser = argparse.ArgumentParser(description="Get data for Challenge DF")
    parser.add_argument("command", choices=["challenge_data"])
    parser.add_argument(
        "CSV_DIR", type=existing_path, help="output directory for challenge.csv"
    )
    parser.add_argument(
        "--DEADLINE",
        type=challenge_date,
        default=None,
        required=False,
        help="""submission deadline.
            Format: YYYY-MM-DD_HOUR:MIN in UTC, or None (use most recent Wed 23:59)
            Example for Round 5: 2023-05-03_23:59
        """,
    )
    parser.add_argument(
        "--RETRIES",
        default=1,
        type=int,
        help="# times to retry failed queries",
        required=False,
    )

    arguments = parser.parse_args()
    print_arguments(arguments)

    print(f"Hardcoded values:" f"\n CHAINID={MUMBAI_CHAINID}" "\n")

    csv_dir = arguments.CSV_DIR

    # extract envvars
    ADDRESS_FILE = _getAddressEnvvarOrExit()

    web3 = networkutil.chain_id_to_web3(MUMBAI_CHAINID)
    record_deployed_contracts(ADDRESS_FILE, MUMBAI_CHAINID)
    judge_acct = judge.get_judge_acct()

    # main work
    deadline_dt = judge.parse_deadline_str(arguments.DEADLINE)
    challenge_data = retry_function(
        judge.get_challenge_data, arguments.RETRIES, 10, web3, deadline_dt, judge_acct
    )

    save_challenge_data_csv(challenge_data, csv_dir)

    print("dftool challenge_data: Done")


# ========================================================================
@enforce_types
def do_predictoor_data():
    parser = argparse.ArgumentParser(description="Get data for Predictoor DF")
    parser.add_argument("command", choices=["predictoor_data"])
    parser.add_argument(
        "ST",
        type=block_or_valid_date,
        help="first block # | YYYY-MM-DD | YYYY-MM-DD_HH:MM",
    )
    parser.add_argument(
        "FIN",
        type=block_or_valid_date,
        help="last block # | YYYY-MM-DD | YYYY-MM-DD_HH:MM | latest",
    )
    parser.add_argument(
        "CSV_DIR",
        type=autocreate_path,
        help="output directory for predictoordata_CHAINID.csv",
    )
    parser.add_argument("CHAINID", type=chain_type, help=CHAINID_EXAMPLES)
    parser.add_argument(
        "--RETRIES",
        default=1,
        type=int,
        help="# times to retry failed queries",
        required=False,
    )

    arguments = parser.parse_args()
    print_arguments(arguments)
    csv_dir, chain_id = arguments.CSV_DIR, arguments.CHAINID

    # check files, prep dir
    _exitIfFileExists(predictoor_data_csv_filename(csv_dir))

    web3 = networkutil.chain_id_to_web3(chain_id)
    st_block, fin_block = get_st_fin_blocks(web3, arguments.ST, arguments.FIN)

    # main work
    predictoor_contracts = retry_function(
        query_predictoor_contracts, arguments.RETRIES, 10, chain_id
    )

    predictoor_data = retry_function(
        query_predictoors,
        arguments.RETRIES,
        10,
        st_block,
        fin_block,
        chain_id,
    )

    save_predictoor_contracts_csv(predictoor_contracts, csv_dir)
    save_predictoor_data_csv(predictoor_data, csv_dir)
    print("dftool predictoor_data: Done")


# ========================================================================


@enforce_types
def do_calc():
    parser = argparse.ArgumentParser(
        description="From substream data files, output rewards csvs."
    )
    parser.add_argument("command", choices=["calc"])
    parser.add_argument("SUBSTREAM", choices=["volume", "challenge"])
    parser.add_argument(
        "CSV_DIR",
        type=existing_path,
        help="output dir for <substream_name>_rewards.csv, etc",
    )
    parser.add_argument(
        "TOT_OCEAN",
        type=float,
        help="total amount of TOKEN to distribute (decimal, not wei)",
    )
    parser.add_argument(
        "--START_DATE",
        type=valid_date_and_convert,
        help="week start date -- YYYY-MM-DD. Used when TOT_OCEAN == 0",
        required=False,
        default=None,
    )

    arguments = parser.parse_args()
    print_arguments(arguments)
    tot_ocean, start_date, csv_dir = (
        arguments.TOT_OCEAN,
        arguments.START_DATE,
        arguments.CSV_DIR,
    )

    # condition inputs
    if tot_ocean == 0 and start_date is None:
        print("TOT_OCEAN == 0, so must give a start date. Exiting.")
        sys.exit(1)

    if tot_ocean == 0:
        # Vesting wallet contract is used to calculate the reward amount for given week / start date
        # currently only deployed on Goerli
        # TODO: should web3 be injected anywhere?
        web3 = networkutil.chain_id_to_web3(5)
        current_dir = os.path.dirname(os.path.abspath(__file__))
        address_path = os.path.join(
            current_dir, "..", "..", ".github", "workflows", "data", "address.json"
        )
        record_deployed_contracts(address_path, chain_id)  # TODO: which chain id?
        tot_ocean = get_active_reward_amount_for_week_eth_by_stream(
            start_date, arguments.SUBSTREAM
        )
        print(
            f"TOT_OCEAN was 0, so re-calc'd: TOT_OCEAN={tot_ocean}"
            f", START_DATE={start_date}"
        )

    if arguments.SUBSTREAM == "volume":
        # do we have the input files?
        required_files = [
            csvs.allocation_csv_filename(csv_dir),
            csvs.vebals_csv_filename(csv_dir),
            *csvs.nftvols_csv_filenames(csv_dir),
            *csvs.owners_csv_filenames(csv_dir),
            *csvs.symbols_csv_filenames(csv_dir),
            *csvs.rate_csv_filenames(csv_dir),
        ]

        for fname in required_files:
            if not os.path.exists(fname):
                print(f"\nNo file {fname} in '{csv_dir}'. Exiting.")
                sys.exit(1)

        # shouldn't already have the output file
        _exitIfFileExists(csvs.volume_rewards_csv_filename(csv_dir))
        _exitIfFileExists(csvs.volume_rewardsinfo_csv_filename(csv_dir))

        rewperlp, rewinfo = calc_rewards_volume(csv_dir, start_date, tot_ocean)

        csvs.save_volume_rewards_csv(rewperlp, csv_dir)
        csvs.save_volume_rewardsinfo_csv(rewinfo, csv_dir)

    if arguments.SUBSTREAM == "challenge":
        try:
            from_addrs, _, _ = load_challenge_data_csv(csv_dir)
        except FileNotFoundError:
            print("Challenge data file not found")
            sys.exit(1)

        if not from_addrs:
            print("No challenge winners found")
            sys.exit(0)
        _exitIfFileExists(challenge_rewards_csv_filename(csv_dir))

        # calculate rewards
        try:
            challenge_rewards = calc_challenge_rewards(from_addrs, start_date)
        except ValueError as e:
            print(e)
            sys.exit(1)

        save_challenge_rewards_csv(challenge_rewards, csv_dir)

    print("dftool calc: Done")


# ========================================================================
@enforce_types
def do_dispense_active():
    parser = argparse.ArgumentParser(
        description="From rewards csv, dispense funds to chain."
    )
    parser.add_argument("command", choices=["dispense_active"])
    parser.add_argument(
        "CSV_DIR", type=existing_path, help="input directory for csv rewards file"
    )
    parser.add_argument(
        "CHAINID",
        type=chain_type,
        help=f"DFRewards contract's network.{CHAINID_EXAMPLES}. If not given, uses 1 (mainnet).",
    )
    parser.add_argument(
        "--DFREWARDS_ADDR",
        default=os.getenv("DFREWARDS_ADDR"),
        type=str,
        help="DFRewards contract's address. If not given, uses envvar DFREWARDS_ADDR",
        required=False,
    )
    parser.add_argument(
        "--TOKEN_ADDR",
        default=os.getenv("TOKEN_ADDR"),
        type=str,
        help="token contract's address. If not given, uses envvar TOKEN_ADDR",
        required=False,
    )
    parser.add_argument(
        "--BATCH_NBR",
        default=None,
        type=str,
        # pylint: disable=line-too-long
        help="specify the batch number to run dispense only for that batch. If not given, runs dispense for all batches.",
        required=False,
    )

    arguments = parser.parse_args()
    print_arguments(arguments)

    assert arguments.DFREWARDS_ADDR is not None
    assert arguments.TOKEN_ADDR is not None

    web3 = networkutil.chain_id_to_web3(arguments.CHAINID)

    # main work
    from_account = _getPrivateAccount()
    web3.eth.default_account = from_account.address
    token_symbol = (
        ContractBase(
            web3, "Simpletoken", web3.to_checksum_address(arguments.TOKEN_ADDR)
        )
        .symbol()
        .upper()
    )
    token_symbol = token_symbol.replace("MOCEAN", "OCEAN")

    volume_rewards = {}
    if os.path.exists(csvs.volume_rewards_csv_filename(arguments.CSV_DIR)):
        volume_rewards_3d = csvs.load_volume_rewards_csv(arguments.CSV_DIR)
        volume_rewards = calc_rewards.flatten_rewards(volume_rewards_3d)

    challenge_rewards = {}
    if os.path.exists(challenge_rewards_csv_filename(arguments.CSV_DIR)):
        challenge_rewards = load_challenge_rewards_csv(arguments.CSV_DIR)
    if len(challenge_rewards) == 0:
        print("Distributing only VOLUME DF rewards")
    else:
        print("Distributing for VOLUME DF and CHALLENGE DF rewards")
    rewards = calc_rewards.merge_rewards(volume_rewards, challenge_rewards)

    # dispense
    dispense.dispense(
        web3,
        rewards,
        web3.to_checksum_address(arguments.DFREWARDS_ADDR),
        web3.to_checksum_address(arguments.TOKEN_ADDR),
        from_account,
        batch_number=arguments.BATCH_NBR,
    )

    print("dftool dispense_active: Done")


# ========================================================================
@enforce_types
def do_new_df_rewards():
    parser = SimpleChainIdArgumentParser(
        "Deploy new DFRewards contract", "new_df_rewards"
    )
    chain_id = parser.print_args_and_get_chain()

    # main work
    web3 = networkutil.chain_id_to_web3(chain_id)
    from_account = _getPrivateAccount()
    web3.eth.default_account = from_account.address
    df_rewards = ContractBase(web3, "DFRewards", constructor_args=[])
    print(f"New DFRewards contract deployed at address: {df_rewards.address}")

    print("dftool new_dfrewards: Done")


# ========================================================================
@enforce_types
def do_new_df_strategy():
    parser = argparse.ArgumentParser(description="Deploy new DFStrategy")
    parser.add_argument("command", choices=["new_df_strategy"])
    parser.add_argument("CHAINID", type=chain_type, help=f"{CHAINID_EXAMPLES}")
    parser.add_argument("DFREWARDS_ADDR", help="DFRewards contract's address")
    parser.add_argument("DFSTRATEGY_NAME", help="DF Strategy name")
    arguments = parser.parse_args()
    print_arguments(arguments)

    web3 = networkutil.chain_id_to_web3(arguments.CHAINID)
    from_account = _getPrivateAccount()
    web3.eth.default_account = from_account.address

    df_strategy = ContractBase(
        web3, arguments.DFSTRATEGY_NAME, constructor_args=[arguments.DFREWARDS_ADDR]
    )
    print(f"New DFStrategy contract deployed at address: {df_strategy.address}")

    print("dftool new_df_strategy: Done")


# ========================================================================
@enforce_types
def do_add_strategy():
    parser = DfStrategyArgumentParser(
        "Add a strategy to DFRewards contract", "addstrategy"
    )

    arguments = parser.parse_args()
    print_arguments(arguments)

    web3 = networkutil.chain_id_to_web3(arguments.CHAINID)
    from_account = _getPrivateAccount()
    df_rewards = ContractBase(web3, "DFRewards", arguments.DFREWARDS_ADDR)

    tx = df_rewards.addStrategy(arguments.DFSTRATEGY_ADDR, {"from": from_account})
    assert tx.events.keys()[0] == "StrategyAdded"

    print(
        f"Strategy {arguments.DFSTRATEGY_ADDR} added to DFRewards {df_rewards.address}"
    )

    print("dftool add_strategy: Done")


# ========================================================================
@enforce_types
def do_retire_strategy():
    parser = DfStrategyArgumentParser(
        "Retire a strategy from DFRewards contract", "retire_strategy"
    )

    arguments = parser.parse_args()
    print_arguments(arguments)

    web3 = networkutil.chain_id_to_web3(arguments.CHAINID)
    from_account = _getPrivateAccount()
    df_rewards = ContractBase(web3, "DFRewards", arguments.DFREWARDS_ADDR)

    tx = df_rewards.retireStrategy(arguments.DFSTRATEGY_ADDR, {"from": from_account})
    # TODO: transform the events part for regular web3, after fixing prev failure
    assert tx.events.keys()[0] == "StrategyRetired"
    print(
        f"Strategy {arguments.DFSTRATEGY_ADDR} retired from DFRewards {df_rewards.address}"
    )

    print("dftool retire_strategy: Done")


# ========================================================================
@enforce_types
def do_init_dev_wallets():
    parser = SimpleChainIdArgumentParser(
        "Init wallets with OCEAN. (GANACHE ONLY)",
        "init_dev_wallets",
        epilog=f"""Uses these envvars:
          ADDRESS_FILE -- eg: export ADDRESS_FILE={networkutil.chain_id_to_address_file(chainID=DEV_CHAINID)}
        """,
    )
    chain_id = parser.print_args_and_get_chain()

    from df_py.util import oceantestutil  # pylint: disable=import-outside-toplevel

    if chain_id != DEV_CHAINID:
        # To support other testnets, they need to init_dev_wallets()
        # Consider this a TODO:)
        print("Only ganache is currently supported. Exiting.")
        sys.exit(1)

    # extract envvars
    ADDRESS_FILE = _getAddressEnvvarOrExit()

    web3 = networkutil.chain_id_to_web3(chain_id)

    # main work
    record_deployed_contracts(ADDRESS_FILE, chain_id)
    # TODO: test this
    oceantestutil.fill_accounts_with_OCEAN(web3.eth.accounts)

    print("dftool init_dev_wallets: Done.")


# ========================================================================
@enforce_types
def do_many_random():
    # UPDATE THIS
    parser = SimpleChainIdArgumentParser(
        "deploy many datatokens + locks OCEAN + allocates + consumes (for testing)",
        "many_random",
        epilog=f"""Uses these envvars:
          ADDRESS_FILE -- eg: export ADDRESS_FILE={networkutil.chain_id_to_address_file(chainID=DEV_CHAINID)}
        """,
    )

    chain_id = parser.print_args_and_get_chain()

    if chain_id != DEV_CHAINID:
        # To support other testnets, they need to fill_accounts_with_OCEAN()
        # Consider this a TODO:)
        print("Only ganache is currently supported. Exiting.")
        sys.exit(1)

    # extract envvars
    ADDRESS_FILE = _getAddressEnvvarOrExit()

    web3 = networkutil.chain_id_to_web3(chain_id)
    from_account = _getPrivateAccount()
    web3.eth.default_account = from_account

    # main work
    record_deployed_contracts(ADDRESS_FILE, chain_id)
    OCEAN = OCEAN_token(chain_id)

    num_nfts = 10  # magic number
    tups = random_create_dataNFT_with_FREs(web3, num_nfts, OCEAN)
    random_lock_and_allocate(web3, tups)
    random_consume_FREs(tups, OCEAN)
    print(f"dftool many_random: Done. {num_nfts} new nfts created.")


# ========================================================================
@enforce_types
def do_mine():
    parser = argparse.ArgumentParser(
        description="Force chain to pass time (ganache only)"
    )
    parser.add_argument("command", choices=["mine"])
    parser.add_argument("TIMEDELTA", type=int, help="e.g. 100")

    arguments = parser.parse_args()
    print_arguments(arguments)

    # main work
    web3 = networkutil.chain_id_to_web3(DEV_CHAINID)
    provider = web3.provider
    provider.make_request("evm_increaseTime", [arguments.TIMEDELTA])
    provider.make_request("evm_mine", [])

    print("dftool mine: Done")


# ========================================================================
@enforce_types
def do_new_acct():
    parser = argparse.ArgumentParser(description="Generate new account")
    parser.add_argument("command", choices=["new_acct"])

    # main work
    web3 = networkutil.chain_id_to_web3(networkutil.DEV_CHAINID)
    account = web3.eth.account.create()

    print("Generated new account:")
    print(f" private_key = {account._private_key.hex()}")
    print(f" address = {account.address}")
    print(f" For other dftools: export DFTOOL_KEY={account._private_key.hex()}")


# ========================================================================
def do_dummy_csvs():
    parser = argparse.ArgumentParser(description="Generate dummy CSVs")
    parser.add_argument("command", choices=["dummy_csvs"])
    parser.add_argument("SUBSTREAM", choices=["volume", "challenge"])
    parser.add_argument(
        "CSV_DIR", type=autocreate_path, help="output dir for csv files"
    )
    arguments = parser.parse_args()
    print_arguments(arguments)

    csv_dir = arguments.CSV_DIR

    if arguments.SUBSTREAM == "challenge":
        save_challenge_data_csv(get_sample_challenge_data(), csv_dir)
        save_challenge_rewards_csv(get_sample_challenge_rewards(), csv_dir)
    else:
        raise NotImplementedError("This substream is not implemented yet.")


# ========================================================================
@enforce_types
def do_new_token():
    parser = argparse.ArgumentParser(description="Generate new token (for testing)")
    parser.add_argument("command", choices=["new_token"])
    parser.add_argument("CHAINID", type=chain_type, help=CHAINID_EXAMPLES)

    arguments = parser.parse_args()
    print_arguments(arguments)

    # main work
    web3 = networkutil.chain_id_to_web3(8996)
    from_account = _getPrivateAccount()
    web3.eth.default_account = from_account.address
    token = ContractBase(
        web3,
        "Simpletoken",
        # TODO: to_wei?
        constructor_args=["TST", "Test Token", 18, to_wei(1e21)],
    )
    print(f"Token '{token.symbol()}' deployed at address: {token.address}")


# ========================================================================
@enforce_types
def do_new_veocean():
    parser = argparse.ArgumentParser(description="Generate new veOcean (for testing)")
    parser.add_argument("command", choices=["new_veocean"])
    parser.add_argument("CHAINID", type=chain_type, help=CHAINID_EXAMPLES)
    parser.add_argument("TOKEN_ADDR", type=str, help="token address")

    arguments = parser.parse_args()
    print_arguments(arguments)

    # main work
    # networkutil.connect(arguments.CHAINID)
    from_account = _getPrivateAccount()

    # deploy veOcean
    veOcean = B.veOcean.deploy(
        arguments.TOKEN_ADDR, "veOCEAN", "veOCEAN", "0.1", {"from": from_account}
    )
    # pylint: disable=line-too-long
    print(
        f"veOcean '{veOcean.symbol()}' deployed at address: {veOcean.address} with token parameter pointing at: {veOcean.token}"
    )


# ========================================================================
@enforce_types
def do_new_veallocate():
    parser = argparse.ArgumentParser(
        description="Generate new veAllocate (for testing)"
    )
    parser.add_argument("command", choices=["new_ve_allocate"])
    parser.add_argument("CHAINID", type=chain_type, help=CHAINID_EXAMPLES)

    arguments = parser.parse_args()
    print_arguments(arguments)

    # main work
    # networkutil.connect(arguments.CHAINID)
    from_account = _getPrivateAccount()
    contract = B.veAllocate.deploy({"from": from_account})
    print(f"veAllocate contract deployed at: {contract.address}")


# ========================================================================
@enforce_types
def do_ve_set_allocation():
    parser = argparse.ArgumentParser(
        description="""
        Allocate weight to veAllocate contract (for testing).
        Set to 0 to trigger resetAllocation event.
    """
    )
    parser.add_argument("command", choices=["ve_set_allocation"])
    parser.add_argument("CHAINID", type=chain_type, help=CHAINID_EXAMPLES)
    parser.add_argument("amount", type=int, help="")
    parser.add_argument("TOKEN_ADDR", type=str, help="NFT Token Address")

    arguments = parser.parse_args()
    print_arguments(arguments)

    # main work
    ADDRESS_FILE = os.environ.get("ADDRESS_FILE")
    if ADDRESS_FILE is not None:
        record_deployed_contracts(ADDRESS_FILE, arguments.CHAINID)
        from_account = _getPrivateAccount()
        veAllocate(arguments.CHAINID).setAllocation(
            arguments.amount,
            Web3.to_checksum_address(arguments.TOKEN_ADDR),
            arguments.CHAINID,
            {"from": from_account},
        )
        allocation = veAllocate(arguments.CHAINID).getTotalAllocation(from_account)
        print(
            "veAllocate current total allocated voting power is: "
            f"{(allocation/10000 * 100)}%"
        )


# ========================================================================
@enforce_types
def do_acct_info():
    parser = argparse.ArgumentParser(
        description="Info about an account",
        epilog="If envvar ADDRESS_FILE is not None, it gives balance for OCEAN token too.",
    )
    parser.add_argument("command", choices=["acct_info"])
    parser.add_argument("CHAINID", type=chain_type, help=CHAINID_EXAMPLES)
    parser.add_argument(
        "ACCOUNT_ADDR",
        type=str,
        help="e.g. '0x987...' or '4'. If the latter, uses accounts[i]",
    )
    parser.add_argument(
        "--TOKEN_ADDR",
        default=os.getenv("TOKEN_ADDR"),
        type=str,
        help="e.g. '0x123..'",
        required=False,
    )

    arguments = parser.parse_args()
    print_arguments(arguments)

    chain_id, account_addr, token_addr = (
        arguments.CHAINID,
        arguments.ACCOUNT_ADDR,
        arguments.TOKEN_ADDR,
    )

    web3 = networkutil.chain_id_to_web3(chain_id)

    if len(account_addr) == 1:
        addr_i = int(account_addr)
        account_addr = web3.to_checksum_address(web3.eth.accounts[addr_i])
    else:
        account_addr = web3.to_checksum_address(account_addr)
    print(f"  Address = {account_addr}")

    if token_addr is not None:
        token = ContractBase(web3, "Simpletoken", web3.to_checksum_address(token_addr))
        balance = token.balanceOf(account_addr)
        print(f"  {from_wei(balance)} {token.symbol()}")

    # Give balance for OCEAN token too.
    ADDRESS_FILE = os.environ.get("ADDRESS_FILE")
    if ADDRESS_FILE is not None:
        record_deployed_contracts(ADDRESS_FILE, chain_id)
        OCEAN = OCEAN_token(chain_id)
        if OCEAN.address != token_addr:
            print(f"  {from_wei(OCEAN.balanceOf(account_addr))} OCEAN")


# ========================================================================
@enforce_types
def do_chain_info():
    parser = argparse.ArgumentParser(description="Info about a network")
    parser.add_argument("command", choices=["chain_info"])
    parser.add_argument("CHAINID", type=chain_type, help=CHAINID_EXAMPLES)

    arguments = parser.parse_args()
    print_arguments(arguments)

    # do work
    web3 = networkutil.chain_id_to_web3(arguments.CHAINID)
    block_number = web3.eth.get_block("latest").number
    print("\nChain info:")
    print(f"  # blocks: {block_number}")


# ========================================================================
@enforce_types
def do_dispense_passive():
    parser = argparse.ArgumentParser(description="Dispense passive rewards")
    parser.add_argument("command", choices=["dispense_passive"])
    parser.add_argument("CHAINID", type=chain_type, help=CHAINID_EXAMPLES)
    parser.add_argument(
        "AMOUNT",
        type=float,
        help="total amount of TOKEN to distribute (decimal, not wei)",
    )
    parser.add_argument(
        "ST", type=valid_date_and_convert, help="week start date -- YYYY-MM-DD"
    )

    arguments = parser.parse_args()
    print_arguments(arguments)

    ADDRESS_FILE = _getAddressEnvvarOrExit()
    record_deployed_contracts(ADDRESS_FILE, arguments.CHAINID)

    amount = arguments.AMOUNT

    if amount == 0:
        start_date = arguments.ST
        amount = get_active_reward_amount_for_week_eth(start_date)

    feedist = FeeDistributor()
    OCEAN = OCEAN_token(arguments.CHAINID)
    retry_function(dispense.dispense_passive, 3, 60, OCEAN, feedist, amount)

    print("Dispensed passive rewards")


# ========================================================================
@enforce_types
def do_calculate_passive():
    parser = argparse.ArgumentParser(description="Calculate passive rewards")
    parser.add_argument("command", choices=["calculate_passive"])
    parser.add_argument("CHAINID", type=chain_type, help=CHAINID_EXAMPLES)
    parser.add_argument("DATE", type=valid_date, help="date in format YYYY-MM-DD")
    parser.add_argument(
        "CSV_DIR",
        type=existing_path,
        help="output dir for passive-CHAINID.csv",
    )

    arguments = parser.parse_args()
    print_arguments(arguments)
    csv_dir = arguments.CSV_DIR

    timestamp = int(timestr_to_timestamp(arguments.DATE))

    S_PER_WEEK = 7 * 86400
    timestamp = timestamp // S_PER_WEEK * S_PER_WEEK
    ADDRESS_FILE = _getAddressEnvvarOrExit()
    record_deployed_contracts(ADDRESS_FILE, arguments.CHAINID)

    # load vebals csv file
    passive_fname = csvs.passive_csv_filename(csv_dir)
    vebals_realtime_fname = csvs.vebals_csv_filename(csv_dir, False)
    if not os.path.exists(vebals_realtime_fname):
        print(f"\nNo file {vebals_realtime_fname} in '{csv_dir}'. Exiting.")
        sys.exit(1)
    _exitIfFileExists(passive_fname)

    # get addresses
    vebals, _, _ = csvs.load_vebals_csv(csv_dir, False)
    addresses = list(vebals.keys())

    balances, rewards = queries.queryPassiveRewards(timestamp, addresses)

    # save to csv
    csvs.save_passive_csv(rewards, balances, csv_dir)


# ========================================================================
@enforce_types
def do_checkpoint_feedist():
    parser = SimpleChainIdArgumentParser(
        "Checkpoint FeeDistributor contract", "checkpoint_feedist"
    )

    chain_id = parser.print_args_and_get_chain()
    web3 = networkutil.chain_id_to_web3(chain_id)

    ADDRESS_FILE = _getAddressEnvvarOrExit()

    record_deployed_contracts(ADDRESS_FILE, chain_id)
    from_account = _getPrivateAccount()
    feedist = FeeDistributor()

    try:
        feedist.checkpoint_total_supply({"from": from_account})
        feedist.checkpoint_token({"from": from_account})

    except Exception as e:  # pylint: disable=broad-exception-caught
        print(f"Checkpoint failed: {e}, submitting tx to multisig")
        total_supply_encoded = feedist.checkpoint_total_supply.encode_input()
        checkpoint_token_encoded = feedist.checkpoint_token.encode_input()

        to = feedist.address
        value = 0
        multisig_addr = chain_id_to_multisig_addr(web3.eth.chain_id)

        # submit transactions to multisig
        retry_function(
            send_multisig_tx, 3, 60, multisig_addr, to, value, total_supply_encoded
        )
        retry_function(
            send_multisig_tx, 3, 60, multisig_addr, to, value, checkpoint_token_encoded
        )

    print("Checkpointed FeeDistributor")


# ========================================================================
# utilities


def _exitIfFileExists(filename: str):
    if os.path.exists(filename):
        print(f"\nFile {filename} exists. Exiting.")
        sys.exit(1)


def _getAddressEnvvarOrExit() -> str:
    ADDRESS_FILE = os.environ.get("ADDRESS_FILE")
    print(f"Envvar:\n ADDRESS_FILE={ADDRESS_FILE}")
    if ADDRESS_FILE is None:
        print(
            "\nNeed to set envvar ADDRESS_FILE. Exiting. "
            f"\nEg: export ADDRESS_FILE={networkutil.chain_id_to_address_file(chainID=DEV_CHAINID)}"
        )
        sys.exit(1)
    return ADDRESS_FILE


def _getSecretSeedOrExit() -> int:
    SECRET_SEED = os.environ.get("SECRET_SEED")
    print(f"Envvar:\n SECRET_SEED={SECRET_SEED}")
    if SECRET_SEED is None:
        print("\nNeed to set envvar SECRET_SEED. Exiting. \nEg: export SECRET_SEED=1")
        sys.exit(1)
    return int(SECRET_SEED)


@enforce_types
def _getPrivateAccount():
    private_key = os.getenv("DFTOOL_KEY")
    assert private_key is not None, "Need to set envvar DFTOOL_KEY"
    account = Account.from_key(private_key=private_key)
    print(f"For private key DFTOOL_KEY, address is: {account.address}")
    return account


@enforce_types
def _do_main():
    if len(sys.argv) <= 1 or sys.argv[1] == "help":
        do_help_long(0)

    func_name = f"do_{sys.argv[1]}"
    func = globals().get(func_name)
    if func is None:
        do_help_long(1)

    func()
