# pylint: disable=too-many-lines,too-many-statements
import argparse
import os
import sys

import brownie
from enforce_typing import enforce_types
from web3.middleware import geth_poa_middleware

from df_py.challenge import judge
from df_py.challenge.calcrewards import calc_challenge_rewards
from df_py.challenge.csvs import (
    challenge_rewards_csv_filename,
    load_challenge_data_csv,
    save_challenge_data_csv,
    save_challenge_rewards_csv,
)
from df_py.predictoor.calcrewards import calc_predictoor_rewards
from df_py.predictoor.csvs import (
    load_predictoor_data_csv,
    load_predictoor_rewards_csv,
    predictoor_data_csv_filename,
    predictoor_rewards_csv_filename,
    save_predictoor_data_csv,
    save_predictoor_rewards_csv,
)
from df_py.predictoor.queries import queryPredictoors
from df_py.util import blockrange, dispense, getrate, networkutil
from df_py.util.base18 import from_wei
from df_py.util.blocktime import getfinBlock, getstfinBlocks, timestrToTimestamp
from df_py.util.constants import BROWNIE_PROJECT as B
from df_py.util.dftool_arguments import (
    CHAINID_EXAMPLES,
    DfStrategyArgumentParser,
    SimpleChainIdArgumentParser,
    StartFinArgumentParser,
    autocreate_path,
    block_or_valid_date,
    challenge_date,
    do_help_long,
    existing_path,
    print_arguments,
    valid_date,
    valid_date_and_convert,
)
from df_py.util.multisig import send_multisig_tx
from df_py.util.networkutil import DEV_CHAINID, chainIdToMultisigAddr
from df_py.util.oceantestutil import (
    randomConsumeFREs,
    randomCreateDataNFTWithFREs,
    randomLockAndAllocate,
)
from df_py.util.oceanutil import (
    FeeDistributor,
    OCEANtoken,
    recordDeployedContracts,
    veAllocate,
)
from df_py.util.retry import retryFunction
from df_py.util.vesting_schedule import (
    getActiveRewardAmountForWeekEth,
    getActiveRewardAmountForWeekEthByStream,
)
from df_py.volume import calcrewards, csvs, queries
from df_py.volume.calcrewards import calc_rewards_volume

brownie.network.web3.middleware_onion.inject(geth_poa_middleware, layer=0)


@enforce_types
def do_volsym():
    parser = StartFinArgumentParser(
        description="Query chain, output volumes, symbols, owners",
        epilog=f"""Uses these envvars:
          \nADDRESS_FILE -- eg: export ADDRESS_FILE={networkutil.chainIdToAddressFile(chainID=DEV_CHAINID)}
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

    CSV_DIR, CHAINID = arguments.CSV_DIR, arguments.CHAINID

    # check files, prep dir
    if not csvs.rate_csv_filenames(CSV_DIR):
        print("\nRates don't exist. Call 'dftool getrate' first. Exiting.")
        sys.exit(1)

    # brownie setup
    networkutil.connect(CHAINID)
    chain = brownie.network.chain
    recordDeployedContracts(ADDRESS_FILE)

    # main work
    rng = blockrange.create_range(
        chain, arguments.ST, arguments.FIN, arguments.NSAMP, SECRET_SEED
    )
    (Vi, Ci, SYMi) = retryFunction(
        queries.queryVolsOwnersSymbols, arguments.RETRIES, 60, rng, CHAINID
    )

    csvs.save_nftvols_csv(Vi, CSV_DIR, CHAINID)
    csvs.save_owners_csv(Ci, CSV_DIR, CHAINID)
    csvs.save_symbols_csv(SYMi, CSV_DIR, CHAINID)

    print("dftool volsym: Done")


# ========================================================================


@enforce_types
def do_nftinfo():
    parser = argparse.ArgumentParser(description="Query chain, output nft info csv")
    parser.add_argument("command", choices=["nftinfo"])
    parser.add_argument(
        "CSV_DIR", type=autocreate_path, help="output dir for nftinfo-CHAINID.csv, etc"
    )
    parser.add_argument("CHAINID", type=int, help=CHAINID_EXAMPLES)
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
    CSV_DIR, CHAINID, ENDBLOCK = arguments.CSV_DIR, arguments.CHAINID, arguments.FIN

    # hardcoded values
    # -queries.queryNftinfo() can be problematic; it's only used for frontend data
    # -so retry 3 times with 10s delay by default
    RETRIES = 3
    DELAY_S = 10
    print(f"Hardcoded values:" f"\n RETRIES={RETRIES}" f"\n DELAY_S={DELAY_S}" "\n")

    # brownie setup
    networkutil.connect(CHAINID)
    chain = brownie.network.chain

    # update ENDBLOCK
    ENDBLOCK = getfinBlock(chain, ENDBLOCK)
    print("Updated ENDBLOCK, new value = {ENDBLOCK}")

    # main work
    nftinfo = retryFunction(queries.queryNftinfo, RETRIES, DELAY_S, CHAINID, ENDBLOCK)
    csvs.save_nftinfo_csv(nftinfo, CSV_DIR, CHAINID)

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

    CSV_DIR, NSAMP, CHAINID = arguments.CSV_DIR, arguments.NSAMP, arguments.CHAINID

    # extract envvars
    SECRET_SEED = _getSecretSeedOrExit()

    _exitIfFileExists(csvs.allocation_csv_filename(CSV_DIR, NSAMP > 1))

    # brownie setup
    networkutil.connect(CHAINID)
    chain = brownie.network.chain

    # main work
    rng = blockrange.create_range(
        chain, arguments.ST, arguments.FIN, NSAMP, SECRET_SEED
    )
    allocs = retryFunction(
        queries.queryAllocations, arguments.RETRIES, 10, rng, CHAINID
    )
    csvs.save_allocation_csv(allocs, CSV_DIR, NSAMP > 1)

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

    CSV_DIR, NSAMP, CHAINID = arguments.CSV_DIR, arguments.NSAMP, arguments.CHAINID

    # extract envvars
    SECRET_SEED = _getSecretSeedOrExit()

    _exitIfFileExists(csvs.vebals_csv_filename(CSV_DIR, NSAMP > 1))

    # brownie setup
    networkutil.connect(CHAINID)
    chain = brownie.network.chain
    rng = blockrange.create_range(
        chain, arguments.ST, arguments.FIN, NSAMP, SECRET_SEED
    )

    balances, locked_amt, unlock_time = retryFunction(
        queries.queryVebalances, arguments.RETRIES, 10, rng, CHAINID
    )
    csvs.save_vebals_csv(balances, locked_amt, unlock_time, CSV_DIR, NSAMP > 1)

    print("dftool vebals: Done")


# ========================================================================
@enforce_types
def do_getrate():
    parser = argparse.ArgumentParser(
        description="Get exchange rate, and output rate csv"
    )
    parser.add_argument("command", choices=["getrate"])
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

    TOKEN_SYMBOL, CSV_DIR = arguments.TOKEN_SYMBOL, arguments.CSV_DIR

    # check files, prep dir
    _exitIfFileExists(csvs.rate_csv_filename(TOKEN_SYMBOL, CSV_DIR))

    # main work
    rate = retryFunction(
        getrate.getrate,
        arguments.RETRIES,
        60,
        TOKEN_SYMBOL,
        arguments.ST,
        arguments.FIN,
    )
    print(f"rate = ${rate:.4f} / {TOKEN_SYMBOL}")
    csvs.save_rate_csv(TOKEN_SYMBOL, rate, CSV_DIR)

    print("dftool getrate: Done")


# ========================================================================
@enforce_types
def do_challenge_data():
    # hardcoded values
    CHAINID = 80001  # only on mumbai
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

    arguments = parser.parse_args()
    print_arguments(arguments)

    print(f"Hardcoded values:" f"\n CHAINID={CHAINID}" "\n")

    CSV_DIR = arguments.CSV_DIR

    # extract envvars
    ADDRESS_FILE = _getAddressEnvvarOrExit()

    if judge.DFTOOL_TEST_FAKE_CSVDIR in CSV_DIR:
        challenge_data = judge.DFTOOL_TEST_FAKE_CHALLENGE_DATA
    else:  # main path
        # brownie setup
        networkutil.connect(CHAINID)
        recordDeployedContracts(ADDRESS_FILE)
        judge_acct = judge.get_judge_acct()

        # main work
        deadline_dt = judge.parse_deadline_str(arguments.DEADLINE)
        challenge_data = judge.get_challenge_data(deadline_dt, judge_acct)

    save_challenge_data_csv(challenge_data, CSV_DIR)

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
    parser.add_argument("CHAINID", type=int, help=CHAINID_EXAMPLES)
    parser.add_argument(
        "--RETRIES",
        default=1,
        type=int,
        help="# times to retry failed queries",
        required=False,
    )

    arguments = parser.parse_args()
    print_arguments(arguments)
    CSV_DIR, CHAINID = arguments.CSV_DIR, arguments.CHAINID

    # check files, prep dir
    _exitIfFileExists(predictoor_data_csv_filename(CSV_DIR))

    # brownie setup
    networkutil.connect(CHAINID)
    chain = brownie.network.chain

    st_block, fin_block = getstfinBlocks(chain, arguments.ST, arguments.FIN)

    # main work
    predictoor_data = retryFunction(
        queryPredictoors,
        arguments.RETRIES,
        10,
        st_block,
        fin_block,
        CHAINID,
    )
    save_predictoor_data_csv(predictoor_data, CSV_DIR)
    print("dftool predictoor_data: Done")


# ========================================================================


@enforce_types
def do_calc():
    parser = argparse.ArgumentParser(
        description="From substream data files, output rewards csvs."
    )
    parser.add_argument("command", choices=["calc"])
    parser.add_argument("SUBSTREAM", choices=["volume", "challenge", "predictoor"])
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
    TOT_OCEAN, START_DATE, CSV_DIR = (
        arguments.TOT_OCEAN,
        arguments.START_DATE,
        arguments.CSV_DIR,
    )

    # condition inputs
    if TOT_OCEAN == 0 and START_DATE is None:
        print("TOT_OCEAN == 0, so must give a start date. Exiting.")
        sys.exit(1)

    if TOT_OCEAN == 0:
        # brownie setup

        # Vesting wallet contract is used to calculate the reward amount for given week / start date
        # currently only deployed on Goerli
        networkutil.connect(5)
        current_dir = os.path.dirname(os.path.abspath(__file__))
        address_path = os.path.join(
            current_dir, "..", "..", ".github", "workflows", "data", "address.json"
        )
        recordDeployedContracts(address_path)
        TOT_OCEAN = getActiveRewardAmountForWeekEthByStream(
            START_DATE, arguments.SUBSTREAM
        )
        print(
            f"TOT_OCEAN was 0, so re-calc'd: TOT_OCEAN={TOT_OCEAN}"
            f", START_DATE={START_DATE}"
        )

    if arguments.SUBSTREAM == "volume":
        # do we have the input files?
        required_files = [
            csvs.allocation_csv_filename(CSV_DIR),
            csvs.vebals_csv_filename(CSV_DIR),
            *csvs.nftvols_csv_filenames(CSV_DIR),
            *csvs.owners_csv_filenames(CSV_DIR),
            *csvs.symbols_csv_filenames(CSV_DIR),
            *csvs.rate_csv_filenames(CSV_DIR),
        ]

        for fname in required_files:
            if not os.path.exists(fname):
                print(f"\nNo file {fname} in '{CSV_DIR}'. Exiting.")
                sys.exit(1)

        # shouldn't already have the output file
        _exitIfFileExists(csvs.volume_rewards_csv_filename(CSV_DIR))
        _exitIfFileExists(csvs.volume_rewardsinfo_csv_filename(CSV_DIR))

        rewperlp, rewinfo = calc_rewards_volume(CSV_DIR, START_DATE, TOT_OCEAN)

        csvs.save_volume_rewards_csv(rewperlp, CSV_DIR)
        csvs.save_volume_rewardsinfo_csv(rewinfo, CSV_DIR)

    if arguments.SUBSTREAM == "challenge":
        from_addrs, _, _ = load_challenge_data_csv(CSV_DIR)
        if not from_addrs:
            print("No challenge winners found")
            sys.exit(0)
        _exitIfFileExists(challenge_rewards_csv_filename(CSV_DIR))

        # calculate rewards
        try:
            challenge_rewards = calc_challenge_rewards(from_addrs, START_DATE)
        except ValueError as e:
            print(e)
            sys.exit(1)

        save_challenge_rewards_csv(challenge_rewards, CSV_DIR)

    if arguments.SUBSTREAM == "predictoor":
        predictoors = load_predictoor_data_csv(CSV_DIR)
        if len(predictoors) == 0:
            print("No predictoors found")
            sys.exit(1)
        _exitIfFileExists(predictoor_rewards_csv_filename(CSV_DIR))

        # calculate rewards
        predictoor_rewards = calc_predictoor_rewards(predictoors, TOT_OCEAN)
        save_predictoor_rewards_csv(predictoor_rewards, CSV_DIR)

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
        type=int,
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

    # brownie setup
    networkutil.connect(arguments.CHAINID)

    # main work
    from_account = _getPrivateAccount()
    token_symbol = B.Simpletoken.at(arguments.TOKEN_ADDR).symbol().upper()
    token_symbol = token_symbol.replace("MOCEAN", "OCEAN")

    volume_rewards = {}
    if os.path.exists(csvs.volume_rewards_csv_filename(arguments.CSV_DIR)):
        volume_rewards_3d = csvs.load_volume_rewards_csv(arguments.CSV_DIR)
        volume_rewards = calcrewards.flattenRewards(volume_rewards_3d)

    predictoor_rewards = {}
    if os.path.exists(predictoor_rewards_csv_filename(arguments.CSV_DIR)):
        predictoor_rewards = load_predictoor_rewards_csv(arguments.CSV_DIR)

    rewards = calcrewards.merge_rewards(volume_rewards, predictoor_rewards)

    # dispense
    dispense.dispense(
        rewards,
        arguments.DFREWARDS_ADDR,
        arguments.TOKEN_ADDR,
        from_account,
        batch_number=arguments.BATCH_NBR,
    )

    print("dftool dispense_active: Done")


# ========================================================================
@enforce_types
def do_newdfrewards():
    parser = SimpleChainIdArgumentParser(
        "Deploy new DFRewards contract", "newdfrewards"
    )
    CHAINID = parser.print_args_and_get_chain()

    # main work
    networkutil.connect(CHAINID)
    from_account = _getPrivateAccount()
    df_rewards = B.DFRewards.deploy({"from": from_account})
    print(f"New DFRewards contract deployed at address: {df_rewards.address}")

    print("dftool newdfrewards: Done")


# ========================================================================
@enforce_types
def do_newdfstrategy():
    parser = argparse.ArgumentParser(description="Deploy new DFStrategy")
    parser.add_argument("command", choices=["newdfstrategy"])
    parser.add_argument("CHAINID", type=int, help=f"{CHAINID_EXAMPLES}")
    parser.add_argument("DFREWARDS_ADDR", help="DFRewards contract's address")
    parser.add_argument("DFSTRATEGY_NAME", help="DF Strategy name")
    arguments = parser.parse_args()
    print_arguments(arguments)

    networkutil.connect(arguments.CHAINID)
    from_account = _getPrivateAccount()
    df_strategy = B[arguments.DFSTRATEGY_NAME].deploy(
        arguments.DFREWARDS_ADDR, {"from": from_account}
    )
    print(f"New DFStrategy contract deployed at address: {df_strategy.address}")

    print("dftool newdfstrategy: Done")


# ========================================================================
@enforce_types
def do_addstrategy():
    parser = DfStrategyArgumentParser(
        "Add a strategy to DFRewards contract", "addstrategy"
    )

    arguments = parser.parse_args()
    print_arguments(arguments)

    networkutil.connect(arguments.CHAINID)
    from_account = _getPrivateAccount()
    df_rewards = B.DFRewards.at(arguments.DFREWARDS_ADDR)
    tx = df_rewards.addStrategy(arguments.DFSTRATEGY_ADDR, {"from": from_account})
    assert tx.events.keys()[0] == "StrategyAdded"

    print(
        f"Strategy {arguments.DFSTRATEGY_ADDR} added to DFRewards {df_rewards.address}"
    )

    print("dftool addstrategy: Done")


# ========================================================================
@enforce_types
def do_retirestrategy():
    parser = DfStrategyArgumentParser(
        "Retire a strategy from DFRewards contract", "retirestrategy"
    )

    arguments = parser.parse_args()
    print_arguments(arguments)

    networkutil.connect(arguments.CHAINID)
    from_account = _getPrivateAccount()
    df_rewards = B.DFRewards.at(arguments.DFREWARDS_ADDR)
    tx = df_rewards.retireStrategy(arguments.DFSTRATEGY_ADDR, {"from": from_account})
    assert tx.events.keys()[0] == "StrategyRetired"
    print(
        f"Strategy {arguments.DFSTRATEGY_ADDR} retired from DFRewards {df_rewards.address}"
    )

    print("dftool addstrategy: Done")


# ========================================================================
@enforce_types
def do_compile():
    parser = argparse.ArgumentParser(description="Compile contracts")
    parser.add_argument("command", choices=["compile"])

    os.system("brownie compile")


# ========================================================================
@enforce_types
def do_initdevwallets():
    # UPADATE THIS
    parser = SimpleChainIdArgumentParser(
        "Init wallets with OCEAN. (GANACHE ONLY)",
        "initdevwallets",
        epilog=f"""Uses these envvars:
          ADDRESS_FILE -- eg: export ADDRESS_FILE={networkutil.chainIdToAddressFile(chainID=DEV_CHAINID)}
        """,
    )
    CHAINID = parser.print_args_and_get_chain()

    from df_py.util import oceantestutil  # pylint: disable=import-outside-toplevel

    if CHAINID != DEV_CHAINID:
        # To support other testnets, they need to initdevwallets()
        # Consider this a TODO:)
        print("Only ganache is currently supported. Exiting.")
        sys.exit(1)

    # extract envvars
    ADDRESS_FILE = _getAddressEnvvarOrExit()

    # brownie setup
    networkutil.connect(CHAINID)

    # main work
    recordDeployedContracts(ADDRESS_FILE)
    oceantestutil.fillAccountsWithOCEAN()

    print("dftool initdevwallets: Done.")


# ========================================================================
@enforce_types
def do_manyrandom():
    # UPDATE THIS
    parser = SimpleChainIdArgumentParser(
        "deploy many datatokens + locks OCEAN + allocates + consumes (for testing)",
        "manyrandom",
        epilog=f"""Uses these envvars:
          ADDRESS_FILE -- eg: export ADDRESS_FILE={networkutil.chainIdToAddressFile(chainID=DEV_CHAINID)}
        """,
    )

    CHAINID = parser.print_args_and_get_chain()

    if CHAINID != DEV_CHAINID:
        # To support other testnets, they need to fillAccountsWithOcean()
        # Consider this a TODO:)
        print("Only ganache is currently supported. Exiting.")
        sys.exit(1)

    # extract envvars
    ADDRESS_FILE = _getAddressEnvvarOrExit()

    # brownie setup
    networkutil.connect(CHAINID)

    # main work
    recordDeployedContracts(ADDRESS_FILE)
    OCEAN = OCEANtoken()

    num_nfts = 10  # magic number
    tups = randomCreateDataNFTWithFREs(num_nfts, OCEAN, brownie.network.accounts)
    randomLockAndAllocate(tups)
    randomConsumeFREs(tups, OCEAN)
    print(f"dftool manyrandom: Done. {num_nfts} new nfts created.")


# ========================================================================
@enforce_types
def do_mine():
    parser = argparse.ArgumentParser(
        description="Force chain to pass time (ganache only)"
    )
    parser.add_argument("command", choices=["mine"])
    parser.add_argument("BLOCKS", type=int, help="e.g. 3")
    parser.add_argument(
        "--TIMEDELTA", type=int, help="e.g. 100", default=None, required=False
    )

    arguments = parser.parse_args()
    print_arguments(arguments)

    BLOCKS, TIMEDELTA = arguments.BLOCKS, arguments.TIMEDELTA

    # main work
    networkutil.connectDev()
    chain = brownie.network.chain
    if TIMEDELTA is not None:
        chain.mine(blocks=BLOCKS, timedelta=TIMEDELTA)
    else:
        chain.mine(blocks=BLOCKS)

    print("dftool mine: Done")


# ========================================================================
@enforce_types
def do_newacct():
    parser = argparse.ArgumentParser(description="Generate new account")
    parser.add_argument("command", choices=["newacct"])

    # main work
    networkutil.connectDev()
    account = brownie.network.accounts.add()

    print("Generated new account:")
    print(f" private_key = {account.private_key}")
    print(f" address = {account.address}")
    print(f" For other dftools: export DFTOOL_KEY={account.private_key}")


# ========================================================================
@enforce_types
def do_newtoken():
    parser = argparse.ArgumentParser(description="Generate new token (for testing)")
    parser.add_argument("command", choices=["newtoken"])
    parser.add_argument("CHAINID", type=int, help=CHAINID_EXAMPLES)

    arguments = parser.parse_args()
    print_arguments(arguments)

    # main work
    networkutil.connect(arguments.CHAINID)
    from_account = _getPrivateAccount()
    token = B.Simpletoken.deploy("TST", "Test Token", 18, 1e21, {"from": from_account})
    print(f"Token '{token.symbol()}' deployed at address: {token.address}")


# ========================================================================
@enforce_types
def do_newVeOcean():
    parser = argparse.ArgumentParser(description="Generate new veOcean (for testing)")
    parser.add_argument("command", choices=["newVeOcean"])
    parser.add_argument("CHAINID", type=int, help=CHAINID_EXAMPLES)
    parser.add_argument("TOKEN_ADDR", type=str, help="token address")

    arguments = parser.parse_args()
    print_arguments(arguments)

    # main work
    networkutil.connect(arguments.CHAINID)
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
def do_newVeAllocate():
    parser = argparse.ArgumentParser(
        description="Generate new veAllocate (for testing)"
    )
    parser.add_argument("command", choices=["newVeAllocate"])
    parser.add_argument("CHAINID", type=int, help=CHAINID_EXAMPLES)

    arguments = parser.parse_args()
    print_arguments(arguments)

    # main work
    networkutil.connect(arguments.CHAINID)
    from_account = _getPrivateAccount()
    contract = B.veAllocate.deploy({"from": from_account})
    print(f"veAllocate contract deployed at: {contract.address}")


# ========================================================================
@enforce_types
def do_veSetAllocation():
    parser = argparse.ArgumentParser(
        description="""
        Allocate weight to veAllocate contract (for testing).
        Set to 0 to trigger resetAllocation event.
    """
    )
    parser.add_argument("command", choices=["veSetAllocation"])
    parser.add_argument("CHAINID", type=int, help=CHAINID_EXAMPLES)
    parser.add_argument("amount", type=float, help="")
    parser.add_argument("TOKEN_ADDR", type=str, help="NFT Token Address")

    arguments = parser.parse_args()
    print_arguments(arguments)

    # main work
    networkutil.connect(arguments.CHAINID)
    ADDRESS_FILE = os.environ.get("ADDRESS_FILE")
    if ADDRESS_FILE is not None:
        recordDeployedContracts(ADDRESS_FILE)
        from_account = _getPrivateAccount()
        veAllocate().setAllocation(
            arguments.amount,
            arguments.TOKEN_ADDR,
            arguments.CHAINID,
            {"from": from_account},
        )
        allocation = veAllocate().getTotalAllocation(from_account)
        print(
            "veAllocate current total allocated voting power is: "
            f"{(allocation/10000 * 100)}%"
        )


# ========================================================================
@enforce_types
def do_acctinfo():
    parser = argparse.ArgumentParser(
        description="Info about an account",
        epilog="If envvar ADDRESS_FILE is not None, it gives balance for OCEAN token too.",
    )
    parser.add_argument("command", choices=["acctinfo"])
    parser.add_argument("CHAINID", type=int, help=CHAINID_EXAMPLES)
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

    CHAINID, ACCOUNT_ADDR, TOKEN_ADDR = (
        arguments.CHAINID,
        arguments.ACCOUNT_ADDR,
        arguments.TOKEN_ADDR,
    )

    networkutil.connect(CHAINID)
    if len(ACCOUNT_ADDR) == 1:
        addr_i = int(ACCOUNT_ADDR)
        ACCOUNT_ADDR = brownie.accounts[addr_i]
    print(f"  Address = {ACCOUNT_ADDR}")

    if TOKEN_ADDR is not None:
        token = B.Simpletoken.at(TOKEN_ADDR)
        balance = token.balanceOf(ACCOUNT_ADDR)
        print(f"  {from_wei(balance)} {token.symbol()}")

    # Give balance for OCEAN token too.
    ADDRESS_FILE = os.environ.get("ADDRESS_FILE")
    if ADDRESS_FILE is not None:
        recordDeployedContracts(ADDRESS_FILE)
        OCEAN = OCEANtoken()
        if OCEAN.address != TOKEN_ADDR:
            print(f"  {from_wei(OCEAN.balanceOf(ACCOUNT_ADDR))} OCEAN")


# ========================================================================
@enforce_types
def do_chaininfo():
    parser = argparse.ArgumentParser(description="Info about a network")
    parser.add_argument("command", choices=["chaininfo"])
    parser.add_argument("CHAINID", type=int, help=CHAINID_EXAMPLES)

    arguments = parser.parse_args()
    print_arguments(arguments)

    # do work
    networkutil.connect(arguments.CHAINID)
    # blocks = len(brownie.network.chain)
    print("\nChain info:")
    print(f"  # blocks: {len(brownie.network.chain)}")


# ========================================================================
@enforce_types
def do_dispense_passive():
    parser = argparse.ArgumentParser(description="Dispense passive rewards")
    parser.add_argument("command", choices=["dispense_passive"])
    parser.add_argument("CHAINID", type=int, help=CHAINID_EXAMPLES)
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

    networkutil.connect(arguments.CHAINID)

    ADDRESS_FILE = _getAddressEnvvarOrExit()
    recordDeployedContracts(ADDRESS_FILE)

    AMOUNT = arguments.AMOUNT

    if AMOUNT == 0:
        START_DATE = arguments.ST
        AMOUNT = getActiveRewardAmountForWeekEth(START_DATE)

    feedist = FeeDistributor()
    OCEAN = OCEANtoken()
    retryFunction(dispense.dispense_passive, 3, 60, OCEAN, feedist, AMOUNT)

    print("Dispensed passive rewards")


# ========================================================================
@enforce_types
def do_calculate_passive():
    parser = argparse.ArgumentParser(description="Calculate passive rewards")
    parser.add_argument("command", choices=["calculate_passive"])
    parser.add_argument("CHAINID", type=int, help=CHAINID_EXAMPLES)
    parser.add_argument("DATE", type=valid_date, help="date in format YYYY-MM-DD")
    parser.add_argument(
        "CSV_DIR",
        type=existing_path,
        help="output dir for passive-CHAINID.csv",
    )

    arguments = parser.parse_args()
    print_arguments(arguments)
    CSV_DIR = arguments.CSV_DIR

    networkutil.connect(arguments.CHAINID)
    timestamp = int(timestrToTimestamp(arguments.DATE))

    S_PER_WEEK = 7 * 86400
    timestamp = timestamp // S_PER_WEEK * S_PER_WEEK
    ADDRESS_FILE = _getAddressEnvvarOrExit()
    recordDeployedContracts(ADDRESS_FILE)

    # load vebals csv file
    passive_fname = csvs.passive_csv_filename(CSV_DIR)
    vebals_realtime_fname = csvs.vebals_csv_filename(CSV_DIR, False)
    if not os.path.exists(vebals_realtime_fname):
        print(f"\nNo file {vebals_realtime_fname} in '{CSV_DIR}'. Exiting.")
        sys.exit(1)
    _exitIfFileExists(passive_fname)

    # get addresses
    vebals, _, _ = csvs.load_vebals_csv(CSV_DIR, False)
    addresses = list(vebals.keys())

    balances, rewards = queries.queryPassiveRewards(timestamp, addresses)

    # save to csv
    csvs.save_passive_csv(rewards, balances, CSV_DIR)


# ========================================================================
@enforce_types
def do_checkpoint_feedist():
    parser = SimpleChainIdArgumentParser(
        "Checkpoint FeeDistributor contract", "checkpoint_feedist"
    )

    CHAINID = parser.print_args_and_get_chain()
    networkutil.connect(CHAINID)

    ADDRESS_FILE = _getAddressEnvvarOrExit()

    recordDeployedContracts(ADDRESS_FILE)
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
        multisig_addr = chainIdToMultisigAddr(brownie.network.chain.id)

        # submit transactions to multisig
        retryFunction(
            send_multisig_tx, 3, 60, multisig_addr, to, value, total_supply_encoded
        )
        retryFunction(
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
            f"\nEg: export ADDRESS_FILE={networkutil.chainIdToAddressFile(chainID=DEV_CHAINID)}"
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
    account = brownie.network.accounts.add(private_key=private_key)
    print(f"For private key DFTOOL_KEY, address is: {account.address}")
    return account


@enforce_types
def _do_main():
    if sys.argv[1] == "help":
        do_help_long(0)

    func_name = f"do_{sys.argv[1]}"
    func = globals().get(func_name)
    if func is None:
        do_help_long(1)

    func()
