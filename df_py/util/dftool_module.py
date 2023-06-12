# pylint: disable=too-many-lines,too-many-statements
import argparse
import datetime
import functools
import os
import sys

import brownie
from enforce_typing import enforce_types
from web3.middleware import geth_poa_middleware

from df_py.challenge import judge
from df_py.challenge.csvs import save_challenge_data_csv
from df_py.predictoor.csvs import (
    predictoor_data_csv_filename,
    predictoor_rewards_csv_filename,
    save_predictoor_data_csv,
    load_predictoor_data_csv,
    save_predictoor_rewards_csv,
    load_predictoor_rewards_csv,
)
from df_py.predictoor.queries import queryPredictoors
from df_py.predictoor.calcrewards import calc_predictoor_rewards
from df_py.util import blockrange, dispense, getrate, networkutil
from df_py.util.base18 import from_wei
from df_py.util.blocktime import getfinBlock, getstfinBlocks, timestrToTimestamp
from df_py.util.constants import BROWNIE_PROJECT as B
from df_py.util.dftool_arguments import (
    valid_date_and_convert,
    existing_path,
    print_arguments,
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
from df_py.volume import calcrewards, csvs, queries
from df_py.volume.calcrewards import calc_rewards_volume
from df_py.util.vesting_schedule import (
    getActiveRewardAmountForWeekEth,
    getActiveRewardAmountForWeekEthByStream,
)

brownie.network.web3.middleware_onion.inject(geth_poa_middleware, layer=0)

CHAINID_EXAMPLES = (
    f"{DEV_CHAINID} for development, 1 for (eth) mainnet, 137 for polygon"
)

# ========================================================================
HELP_SHORT = """Data Farming tool, for use by OPF.

Usage: dftool compile|getrate|volsym|.. ARG1 ARG2 ..

  dftool help - full command list

  dftool compile - compile contracts
  dftool getrate TOKEN_SYMBOL ST FIN CSV_DIR [RETRIES]
  dftool volsym ST FIN NSAMP CSV_DIR CHAINID [RETRIES] - query chain, output volumes, symbols, owners
  dftool allocations ST FIN NSAMP CSV_DIR CHAINID [RETRIES]
  dftool vebals ST FIN NSAMP CSV_DIR CHAINID [RETRIES]
  dftool challenge_data CSV_DIR [DEADLINE] [RETRIES]
  dftool predictoor_data CSV_DIR START_DATE END_DATE CHAINID [RETRIES]
  dftool calc volume|predictoor|challenge CSV_DIR TOT_OCEAN START_DATE - from stakes/etc csvs (or predictoor/challenge data csvs), output rewards csv for volume, predictoor or challenge substream
  dftool dispense_active CSV_DIR [CHAINID] [DFREWARDS_ADDR] [TOKEN_ADDR] [BATCH_NBR] - from rewards, dispense funds
  dftool dispense_passive CHAINID AMOUNT
  dftool nftinfo CSV_DIR CHAINID -- Query chain, output nft info csv
"""

HELP_LONG = (
    HELP_SHORT
    + """
  dftool newacct - generate new account
  dftool initdevwallets CHAINID - Init wallets with OCEAN. (GANACHE ONLY)
  dftool newtoken CHAINID - generate new token (for testing)
  dftool acctinfo CHAINID ACCOUNT_ADDR [TOKEN_ADDR] - info about an account
  dftool chaininfo CHAINID - info about a network

  dftool mine BLOCKS [TIMEDELTA] - force chain to pass time (ganache only)

  dftool newVeOcean CHAINID TOKEN_ADDR - deploy veOcean using TOKEN_ADDR (for testing)
  dftool newVeAllocate CHAINID - deploy veAllocate (for testing)
  dftool veSetAllocation CHAINID amount exchangeId - Allocate weight to veAllocate contract. Set to 0 to reset. (for testing)

  dftool manyrandom CHAINID - deploy many datatokens + locks OCEAN + allocates + consumes (for testing)
  dftool newdfrewards CHAINID - deploy new DFRewards contract
  dftool newdfstrategy CHAINID DFREWARDS_ADDR DFSTRATEGY_NAME - deploy new DFStrategy
  dftool addstrategy CHAINID DFREWARDS_ADDR DFSTRATEGY_ADDR - Add a strategy to DFRewards contract
  dftool retirestrategy CHAINID DFREWARDS_ADDR DFSTRATEGY_ADDR - Retire a strategy from DFRewards contract
  dftool checkpoint_feedist CHAINID - checkpoint FeeDistributor contract

Transactions are signed with envvar 'DFTOOL_KEY`.
"""
)


@enforce_types
def do_help():
    do_help_long()


@enforce_types
def do_help_short(status_code=0):
    print(HELP_SHORT)
    sys.exit(status_code)


@enforce_types
def do_help_long(status_code=0):
    print(HELP_LONG)
    sys.exit(status_code)


# ========================================================================
@enforce_types
def do_volsym():
    HELP = f"""Query chain, output volumes, symbols, owners

Usage: dftool volsym ST FIN NSAMP CSV_DIR CHAINID [RETRIES]
  ST -- first block # to calc on | YYYY-MM-DD | YYYY-MM-DD_HH:MM
  FIN -- last block # to calc on | YYYY-MM-DD | YYYY-MM-DD_HH:MM | latest
  NSAMP -- # blocks to sample liquidity from, from blocks [ST, ST+1, .., FIN]
  CSV_DIR -- output dir for stakes-CHAINID.csv, etc
  CHAINID -- {CHAINID_EXAMPLES}
  RETRIES -- # times to retry failed queries

Uses these envvars:
  ADDRESS_FILE -- eg: export ADDRESS_FILE={networkutil.chainIdToAddressFile(chainID=DEV_CHAINID)}
  SECRET_SEED -- secret integer used to seed the rng
"""
    if len(sys.argv) not in [2 + 5, 2 + 6]:
        print(HELP)
        sys.exit(1)

    # extract inputs
    assert sys.argv[1] == "volsym"
    ST, FIN, NSAMP = sys.argv[2], sys.argv[3], int(sys.argv[4])
    CSV_DIR = sys.argv[5]
    CHAINID = int(sys.argv[6])
    RETRIES = 1
    if len(sys.argv) == 2 + 6:
        RETRIES = int(sys.argv[7])

    print("dftool volsym: Begin")
    print(
        f"Arguments: "
        f"\n ST={ST}\n FIN={FIN}\n NSAMP={NSAMP}"
        f"\n CSV_DIR={CSV_DIR}"
        f"\n CHAINID={CHAINID}"
        f"\n RETRIES={RETRIES}"
        "\n"
    )

    # extract envvars
    ADDRESS_FILE = _getAddressEnvvarOrExit()
    SECRET_SEED = _getSecretSeedOrExit()

    # check files, prep dir
    if not os.path.exists(CSV_DIR):
        print(f"\nDirectory {CSV_DIR} doesn't exist; nor do rates. Exiting.")
        sys.exit(1)
    if not csvs.rate_csv_filenames(CSV_DIR):
        print("\nRates don't exist. Call 'dftool getrate' first. Exiting.")
        sys.exit(1)

    # brownie setup
    networkutil.connect(CHAINID)
    chain = brownie.network.chain
    recordDeployedContracts(ADDRESS_FILE)

    # main work
    rng = blockrange.create_range(chain, ST, FIN, NSAMP, SECRET_SEED)
    (Vi, Ci, SYMi) = retryFunction(
        queries.queryVolsOwnersSymbols, RETRIES, 60, rng, CHAINID
    )
    csvs.save_nftvols_csv(Vi, CSV_DIR, CHAINID)
    csvs.save_owners_csv(Ci, CSV_DIR, CHAINID)
    csvs.save_symbols_csv(SYMi, CSV_DIR, CHAINID)

    print("dftool volsym: Done")


# ========================================================================


@enforce_types
def do_nftinfo():
    HELP = f"""Query chain, output nft info csv
Usage: dftool nftinfo CSV_DIR CHAINID [FIN]
    CSV_DIR -- output dir for nftinfo-CHAINID.csv
    CHAINID -- {CHAINID_EXAMPLES}
    FIN -- last block # to calc on | YYYY-MM-DD | YYYY-MM-DD_HH:MM | latest
"""
    if len(sys.argv) not in [4, 5]:
        print(HELP)
        sys.exit(1)

    # extract inputs
    assert sys.argv[1] == "nftinfo"
    CSV_DIR = sys.argv[2]
    CHAINID = int(sys.argv[3])
    ENDBLOCK = sys.argv[4] if len(sys.argv) == 5 else "latest"

    print("dftool nftinfo: Begin")
    print(
        f"Arguments: "
        f"\n CSV_DIR={CSV_DIR}"
        f"\n CHAINID={CHAINID}"
        f"\n ENDBLOCK={ENDBLOCK}"
        "\n"
    )

    # hardcoded values
    # -queries.queryNftinfo() can be problematic; it's only used for frontend data
    # -so retry 3 times with 10s delay by default
    RETRIES = 3
    DELAY_S = 10
    print(f"Hardcoded values:" f"\n RETRIES={RETRIES}" f"\n DELAY_S={DELAY_S}" "\n")

    # create dir if not exists
    _createDirIfNeeded(CSV_DIR)

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
    HELP = f"""Query chain, outputs allocation csv

Usage: dftool allocations ST FIN NSAMP CSV_DIR CHAINID [RETRIES]
  ST -- first block # to calc on | YYYY-MM-DD | YYYY-MM-DD_HH:MM
  FIN -- last block # to calc on | YYYY-MM-DD | YYYY-MM-DD_HH:MM | latest
  NSAMP -- # blocks to sample liquidity from, from blocks [ST, ST+1, .., FIN]
  CSV_DIR -- output dir for stakes-CHAINID.csv, etc
  CHAINID -- {CHAINID_EXAMPLES}
  RETRIES -- # times to retry failed queries

Uses these envvars:
  SECRET_SEED -- secret integer used to seed the rng
"""
    if len(sys.argv) not in [7, 8]:
        print(HELP)
        sys.exit(1)

    # extract inputs
    assert sys.argv[1] == "allocations"
    ST, FIN, NSAMP = sys.argv[2], sys.argv[3], int(sys.argv[4])
    CSV_DIR = sys.argv[5]
    CHAINID = int(sys.argv[6])
    RETRIES = 1
    if len(sys.argv) == 8:
        RETRIES = int(sys.argv[7])

    print("dftool do_allocations: Begin")
    print(
        f"Arguments: "
        f"\n ST={ST}\n FIN={FIN}\n NSAMP={NSAMP}"
        f"\n CSV_DIR={CSV_DIR}"
        f"\n CHAINID={CHAINID}"
        f"\n RETRIES={RETRIES}"
        "\n"
    )

    # extract envvars
    SECRET_SEED = _getSecretSeedOrExit()

    # create dir if not exists
    _createDirIfNeeded(CSV_DIR)
    _exitIfFileExists(csvs.allocation_csv_filename(CSV_DIR, NSAMP > 1))

    # brownie setup
    networkutil.connect(CHAINID)
    chain = brownie.network.chain

    # main work
    rng = blockrange.create_range(chain, ST, FIN, NSAMP, SECRET_SEED)
    allocs = retryFunction(queries.queryAllocations, RETRIES, 10, rng, CHAINID)
    csvs.save_allocation_csv(allocs, CSV_DIR, NSAMP > 1)

    print("dftool allocations: Done")


# ========================================================================


@enforce_types
def do_vebals():
    HELP = f"""Query chain, outputs veBalances csv

Usage: dftool vebals ST FIN NSAMP CSV_DIR CHAINID [RETRIES]
  ST -- first block # to calc on | YYYY-MM-DD | YYYY-MM-DD_HH:MM
  FIN -- last block # to calc on | YYYY-MM-DD | YYYY-MM-DD_HH:MM | latest
  NSAMP -- # blocks to sample liquidity from, from blocks [ST, ST+1, .., FIN]
  CSV_DIR -- output dir for stakes-CHAINID.csv, etc
  CHAINID -- {CHAINID_EXAMPLES}
  RETRIES -- # times to retry failed queries

Uses these envvars:
  SECRET_SEED -- secret integer used to seed the rng
"""
    if len(sys.argv) not in [7, 8]:
        print(HELP)
        sys.exit(1)

    # extract inputs
    assert sys.argv[1] == "vebals"
    ST, FIN, NSAMP = sys.argv[2], sys.argv[3], int(sys.argv[4])
    CSV_DIR = sys.argv[5]
    CHAINID = int(sys.argv[6])
    RETRIES = 1
    if len(sys.argv) == 8:
        RETRIES = int(sys.argv[7])

    print("dftool vebals: Begin")
    print(
        f"Arguments: "
        f"\n ST={ST}\n FIN={FIN}\n NSAMP={NSAMP}"
        f"\n CSV_DIR={CSV_DIR}"
        f"\n CHAINID={CHAINID}"
        f"\n RETRIES={RETRIES}"
        "\n"
    )

    # extract envvars
    SECRET_SEED = _getSecretSeedOrExit()

    # create a dir if not exists
    _createDirIfNeeded(CSV_DIR)
    _exitIfFileExists(csvs.vebals_csv_filename(CSV_DIR, NSAMP > 1))

    # brownie setup
    networkutil.connect(CHAINID)
    chain = brownie.network.chain
    rng = blockrange.create_range(chain, ST, FIN, NSAMP, SECRET_SEED)

    balances, locked_amt, unlock_time = retryFunction(
        queries.queryVebalances, RETRIES, 10, rng, CHAINID
    )
    csvs.save_vebals_csv(balances, locked_amt, unlock_time, CSV_DIR, NSAMP > 1)

    print("dftool vebals: Done")


# ========================================================================
@enforce_types
def do_getrate():
    HELP = """Get exchange rate, and output rate csv

Usage: dftool getrate TOKEN_SYMBOL ST FIN CSV_DIR [RETRIES]
  TOKEN_SYMBOL -- e.g. OCEAN, H2O
  ST -- start time -- YYYY-MM-DD
  FIN -- end time -- YYYY-MM-DD
  CSV_DIR -- output directory for rate-TOKEN_SYMBOL.csv file
  RETRIES -- # times to retry failed queries
"""
    if len(sys.argv) not in [2 + 4, 2 + 5]:
        print(HELP)
        sys.exit(1)

    # extract inputs
    assert sys.argv[1] == "getrate"
    TOKEN_SYMBOL = sys.argv[2]
    ST, FIN = sys.argv[3], sys.argv[4]
    CSV_DIR = sys.argv[5]
    RETRIES = 1
    if len(sys.argv) == 2 + 5:
        RETRIES = int(sys.argv[2 + 4])
    print("dftool getrate: Begin")
    print(f"Arguments: ST={ST}, FIN={FIN}, CSV_DIR={CSV_DIR}\n")

    # check files, prep dir
    _exitIfFileExists(csvs.rate_csv_filename(TOKEN_SYMBOL, CSV_DIR))
    _createDirIfNeeded(CSV_DIR)

    # main work
    rate = retryFunction(getrate.getrate, RETRIES, 60, TOKEN_SYMBOL, ST, FIN)
    print(f"rate = ${rate:.4f} / {TOKEN_SYMBOL}")
    csvs.save_rate_csv(TOKEN_SYMBOL, rate, CSV_DIR)

    print("dftool getrate: Done")


# ========================================================================
@enforce_types
def do_challenge_data():
    # hardcoded values
    CHAINID = 80001  # only on mumbai

    HELP = f"""Get data for Challenge DF

Usage: dftool challenge_data CSV_DIR [DEADLINE] [RETRIES]
  CSV_DIR -- output directory for rate-TOKEN_SYMBOL.csv file
  DEADLINE -- submission deadline.
    Format: YYYY-MM-DD_HOUR:MIN in UTC, or None (use most recent Wed 23:59)
    Example for Round 5: 2023-05-03_23:59
  RETRIES -- # times to retry failed queries

Hardcoded values:
  CHAINID = {CHAINID}

Uses these envvars:
  ADDRESS_FILE -- eg: export ADDRESS_FILE={networkutil.chainIdToAddressFile(chainID=CHAINID)}
"""
    if len(sys.argv) not in [2 + 1, 2 + 2, 2 + 3]:
        print(HELP)
        sys.exit(1)

    # extract inputs
    assert sys.argv[1] == "challenge_data"
    CSV_DIR = sys.argv[2]
    DEADLINE = "None" if len(sys.argv) <= 3 else sys.argv[3]
    RETRIES = 1 if len(sys.argv) <= 4 else int(sys.argv[4])
    print("dftool challenge_data: Begin\n")

    print(
        f"Arguments:"
        f"\n CSV_DIR={CSV_DIR}"
        f"\n DEADLINE={DEADLINE}"
        f"\n RETRIES={RETRIES}"
        "\n"
    )

    print(f"Hardcoded values:" f"\n CHAINID={CHAINID}" "\n")

    # extract envvars
    ADDRESS_FILE = _getAddressEnvvarOrExit()

    # check files, prep dir
    if not os.path.exists(CSV_DIR):
        print(f"\nDirectory {CSV_DIR} doesn't exist; nor do rates. Exiting.")
        sys.exit(1)

    if judge.DFTOOL_TEST_FAKE_CSVDIR in CSV_DIR:
        challenge_data = judge.DFTOOL_TEST_FAKE_CHALLENGE_DATA

    else:  # main path
        # brownie setup
        networkutil.connect(CHAINID)
        recordDeployedContracts(ADDRESS_FILE)
        judge_acct = judge.get_judge_acct()

        # main work
        deadline_dt = judge.parse_deadline_str(DEADLINE)
        challenge_data = judge.get_challenge_data(deadline_dt, judge_acct)

    save_challenge_data_csv(challenge_data, CSV_DIR)

    print("dftool challenge_data: Done")


# ========================================================================
@enforce_types
def do_predictoor_data():
    HELP = f"""Get data for Predictoor DF

Usage: dftool predictoor_data CSV_DIR START_DATE END_DATE CHAINID [RETRIES]
  ST -- start time -- YYYY-MM-DD
  FIN -- end time -- YYYY-MM-DD
  CSV_DIR -- output directory for predictoordata_CHAINID.csv file
  CHAINID -- {CHAINID_EXAMPLES}
  RETRIES -- # times to retry failed queries
"""
    if len(sys.argv) not in [2 + 4, 2 + 5]:
        print(HELP)
        sys.exit(1)

    # extract inputs
    assert sys.argv[1] == "predictoor_data"
    CSV_DIR = sys.argv[2]
    ST = sys.argv[3]
    FIN = sys.argv[4]
    CHAINID = int(sys.argv[5])
    print(sys.argv, len(sys.argv))
    RETRIES = 1 if len(sys.argv) == 6 else int(sys.argv[6])
    print("dftool predictoor_data: Begin")
    print(
        f"Arguments: "
        f"\n CSV_DIR={CSV_DIR}"
        f"\n START_DATE={ST}"
        f"\n END_DATE={FIN}"
        f"\n CHAINID={CHAINID}"
        f"\n RETRIES={RETRIES}"
    )

    # check files, prep dir
    _createDirIfNeeded(CSV_DIR)
    _exitIfFileExists(predictoor_data_csv_filename(CSV_DIR))

    # brownie setup
    networkutil.connect(CHAINID)
    chain = brownie.network.chain

    st_block, fin_block = getstfinBlocks(chain, ST, FIN)

    # main work
    predictoor_data = retryFunction(
        queryPredictoors,
        RETRIES,
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

    # challenge df goes here ----------

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
    HELP = f"""From rewards csv, dispense funds to chain

Usage: dftool dispense_active CSV_DIR [CHAINID] [DFREWARDS_ADDR] [TOKEN_ADDR] [BATCH_NBR]
  CSV_DIR -- input directory for csv rewards file
  CHAINID: CHAINID -- DFRewards contract's network.{CHAINID_EXAMPLES}. If not given, uses 1 (mainnet).
  DFREWARDS_ADDR -- DFRewards contract's address. If not given, uses envvar DFREWARDS_ADDR
  TOKEN_ADDR -- token contract's address. If not given, uses envvar TOKEN_ADDR
  BATCH_NBR -- specify the batch number to run dispense only for that batch. If not given, runs dispense for all batches.

Transactions are signed with envvar 'DFTOOL_KEY`.
"""
    if len(sys.argv) not in [4 + 0, 4 + 1, 4 + 2, 4 + 3]:
        print(HELP)
        sys.exit(1)

    # extract inputs
    assert sys.argv[1] == "dispense_active"
    CSV_DIR = sys.argv[2]

    if len(sys.argv) >= 4:
        CHAINID = int(sys.argv[3])
    else:
        CHAINID = 1

    if len(sys.argv) >= 5:
        DFREWARDS_ADDR = sys.argv[4]
    else:
        print("Set DFREWARDS_ADDR from envvar")
        DFREWARDS_ADDR = os.getenv("DFREWARDS_ADDR")

    if len(sys.argv) >= 6:
        TOKEN_ADDR = sys.argv[5]
    else:
        print("Set TOKEN_ADDR from envvar")
        TOKEN_ADDR = os.getenv("TOKEN_ADDR")

    BATCH_NBR = None
    if len(sys.argv) >= 7:
        BATCH_NBR = int(sys.argv[6])

    print(
        f"Arguments: CSV_DIR={CSV_DIR}, CHAINID={CHAINID}"
        f", DFREWARDS_ADDR={DFREWARDS_ADDR}, TOKEN_ADDR={TOKEN_ADDR}"
        f", BATCH_NBR={BATCH_NBR}\n"
    )
    assert DFREWARDS_ADDR is not None
    assert TOKEN_ADDR is not None

    # brownie setup
    networkutil.connect(CHAINID)

    # main work
    from_account = _getPrivateAccount()
    token_symbol = B.Simpletoken.at(TOKEN_ADDR).symbol().upper()
    token_symbol = token_symbol.replace("MOCEAN", "OCEAN")

    volume_rewards = {}
    if os.path.exists(csvs.volume_rewards_csv_filename(CSV_DIR)):
        volume_rewards_3d = csvs.load_volume_rewards_csv(CSV_DIR)
        volume_rewards = calcrewards.flattenRewards(volume_rewards_3d)

    predictoor_rewards = {}
    if os.path.exists(predictoor_rewards_csv_filename(CSV_DIR)):
        predictoor_rewards = load_predictoor_rewards_csv(CSV_DIR)

    rewards = calcrewards.merge_rewards(volume_rewards, predictoor_rewards)

    # dispense
    dispense.dispense(
        rewards,
        DFREWARDS_ADDR,
        TOKEN_ADDR,
        from_account,
        batch_number=BATCH_NBR,
    )

    print("dftool dispense_active: Done")


# ========================================================================
@enforce_types
def do_newdfrewards():
    HELP = f"""Deploy new DFRewards contract

Usage: dftool newdfrewards CHAINID
  CHAINID -- {CHAINID_EXAMPLES}
"""
    if len(sys.argv) not in [3]:
        print(HELP)
        sys.exit(1)

    # extract inputs
    assert sys.argv[1] == "newdfrewards"
    CHAINID = int(sys.argv[2])

    print(f"Arguments: CHAINID={CHAINID}")

    # main work
    networkutil.connect(CHAINID)
    from_account = _getPrivateAccount()
    df_rewards = B.DFRewards.deploy({"from": from_account})
    print(f"New DFRewards contract deployed at address: {df_rewards.address}")

    print("dftool newdfrewards: Done")


# ========================================================================
@enforce_types
def do_newdfstrategy():
    HELP = f"""Deploy new DFStrategy contract

Usage: dftool newdfstrategy CHAINID DFREWARDS_ADDR DFSTRATEGY_NAME
  CHAINID -- {CHAINID_EXAMPLES}
  DFREWARDS_ADDR -- DFRewards contract address
  DFSTRATEGY_NAME -- DFStrategy contract name
"""
    if len(sys.argv) not in [5]:
        print(HELP)
        sys.exit(1)

    assert sys.argv[1] == "newdfstrategy"
    CHAINID = int(sys.argv[2])
    DFREWARDS_ADDR = sys.argv[3]
    DFSTRATEGY_NAME = sys.argv[4]

    print(f"Arguments: CHAINID={CHAINID}")

    networkutil.connect(CHAINID)
    from_account = _getPrivateAccount()
    df_strategy = B[DFSTRATEGY_NAME].deploy(DFREWARDS_ADDR, {"from": from_account})
    print(f"New DFStrategy contract deployed at address: {df_strategy.address}")

    print("dftool newdfstrategy: Done")


# ========================================================================
@enforce_types
def do_addstrategy():
    HELP = f"""Add a strategy to DFRewards contract

Usage: dftool addstrategy CHAINID DFREWARDS_ADDR DFSTRATEGY_ADDR
  CHAINID -- {CHAINID_EXAMPLES}
  DFREWARDS_ADDR -- DFRewards contract address
  DFSTRATEGY_ADDR -- DFStrategy contract address
"""
    if len(sys.argv) not in [5]:
        print(HELP)
        sys.exit(1)

    assert sys.argv[1] == "addstrategy"
    CHAINID = int(sys.argv[2])
    DFREWARDS_ADDR = sys.argv[3]
    DFSTRATEGY_ADDR = sys.argv[4]

    print(f"Arguments: CHAINID={CHAINID}")

    networkutil.connect(CHAINID)
    from_account = _getPrivateAccount()
    df_rewards = B.DFRewards.at(DFREWARDS_ADDR)
    tx = df_rewards.addStrategy(DFSTRATEGY_ADDR, {"from": from_account})
    assert tx.events.keys()[0] == "StrategyAdded"

    print(f"Strategy {DFSTRATEGY_ADDR} added to DFRewards {df_rewards.address}")

    print("dftool addstrategy: Done")


# ========================================================================
@enforce_types
def do_retirestrategy():
    HELP = f"""Retire a strategy from DFRewards contract

Usage: dftool retirestrategy CHAINID DFREWARDS_ADDR DFSTRATEGY_ADDR
  CHAINID -- {CHAINID_EXAMPLES}
  DFREWARDS_ADDR -- DFRewards contract address
  DFSTRATEGY_ADDR -- DFStrategy contract address
"""
    if len(sys.argv) not in [5]:
        print(HELP)
        sys.exit(1)

    assert sys.argv[1] == "retirestrategy"
    CHAINID = int(sys.argv[2])
    DFREWARDS_ADDR = sys.argv[3]
    DFSTRATEGY_ADDR = sys.argv[4]

    print(f"Arguments: CHAINID={CHAINID}")

    networkutil.connect(CHAINID)
    from_account = _getPrivateAccount()
    df_rewards = B.DFRewards.at(DFREWARDS_ADDR)
    tx = df_rewards.retireStrategy(DFSTRATEGY_ADDR, {"from": from_account})
    assert tx.events.keys()[0] == "StrategyRetired"
    print(f"Strategy {DFSTRATEGY_ADDR} retired from DFRewards {df_rewards.address}")

    print("dftool addstrategy: Done")


# ========================================================================
@enforce_types
def do_compile():
    HELP = """Compile contracts

Usage: dftool compile
"""
    if len(sys.argv) not in [2]:
        print(HELP)
        sys.exit(1)

    os.system("brownie compile")


# ========================================================================
@enforce_types
def do_initdevwallets():
    # UPADATE THIS
    HELP = f"""dftool initdevwallets CHAINID - Init wallets with OCEAN. (GANACHE ONLY)

Usage: dftool initdevwallets CHAINID
  CHAINID -- {CHAINID_EXAMPLES}

Uses these envvars:
  ADDRESS_FILE -- eg: export ADDRESS_FILE={networkutil.chainIdToAddressFile(chainID=DEV_CHAINID)}
"""
    if len(sys.argv) not in [3]:
        print(HELP)
        sys.exit(1)

    from df_py.util import oceantestutil  # pylint: disable=import-outside-toplevel

    # extract inputs
    assert sys.argv[1] == "initdevwallets"
    CHAINID = int(sys.argv[2])
    print("dftool initdevwallets: Begin")
    print(f"Arguments: CHAINID={CHAINID}")

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
    HELP = f"""deploy many datatokens + locks OCEAN + allocates + consumes (for testing)

Usage: dftool manyrandom CHAINID
  CHAINID -- {CHAINID_EXAMPLES}

Uses these envvars:
  ADDRESS_FILE -- eg: export ADDRESS_FILE={networkutil.chainIdToAddressFile(chainID=DEV_CHAINID)}
"""
    if len(sys.argv) not in [3]:
        print(HELP)
        sys.exit(1)

    # extract inputs
    assert sys.argv[1] == "manyrandom"
    CHAINID = int(sys.argv[2])
    print("dftool manyrandom: Begin")
    print(f"Arguments: CHAINID={CHAINID}")

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
    HELP = """Force chain to pass time (ganache only)

Usage: dftool mine BLOCKS [TIMEDELTA]
  BLOCKS -- e.g. 3
  TIMEDELTA -- e.g. 100
"""
    if len(sys.argv) not in [3, 4]:
        print(HELP)
        sys.exit(1)

    # extract inputs
    assert sys.argv[1] == "mine"
    BLOCKS = int(sys.argv[2])
    if len(sys.argv) == 4:
        TIMEDELTA = int(sys.argv[3])
    else:
        TIMEDELTA = None

    print(f"Arguments: BLOCKS={BLOCKS}, TIMEDELTA={TIMEDELTA}")

    # main work
    networkutil.connectDev()
    chain = brownie.network.chain
    if TIMEDELTA is None:
        chain.mine(blocks=BLOCKS, timedelta=TIMEDELTA)
    else:
        chain.mine(blocks=BLOCKS)

    print("dftool mine: Done")


# ========================================================================
@enforce_types
def do_newacct():
    HELP = """Generate new account

Usage: dftool newacct
"""
    if len(sys.argv) not in [2]:
        print(HELP)
        sys.exit(1)

    # extract inputs
    assert sys.argv[1] == "newacct"

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
    HELP = """Generate new token (for testing)

Usage: dftool newtoken CHAINID
"""
    if len(sys.argv) not in [3]:
        print(HELP)
        sys.exit(1)

    # extract inputs
    assert sys.argv[1] == "newtoken"
    CHAINID = int(sys.argv[2])
    print(f"Arguments:\n CHAINID={CHAINID}")

    # main work
    networkutil.connect(CHAINID)
    from_account = _getPrivateAccount()
    token = B.Simpletoken.deploy("TST", "Test Token", 18, 1e21, {"from": from_account})
    print(f"Token '{token.symbol()}' deployed at address: {token.address}")


# ========================================================================
@enforce_types
def do_newVeOcean():
    HELP = """Generate new veOcean (for testing)

Usage: dftool newVeOcean CHAINID TOKEN_ADDR
"""
    if len(sys.argv) not in [4]:
        print(HELP)
        sys.exit(1)

    # extract inputs
    assert sys.argv[1] == "newVeOcean"
    CHAINID = int(sys.argv[2])
    print(f"Arguments:\n CHAINID={CHAINID}")

    TOKEN_ADDR = str(sys.argv[3])
    print(f"Arguments:\n TOKEN_ADDR={TOKEN_ADDR}")

    # main work
    networkutil.connect(CHAINID)
    from_account = _getPrivateAccount()

    # deploy veOcean
    veOcean = B.veOcean.deploy(
        TOKEN_ADDR, "veOCEAN", "veOCEAN", "0.1", {"from": from_account}
    )
    # pylint: disable=line-too-long
    print(
        f"veOcean '{veOcean.symbol()}' deployed at address: {veOcean.address} with token parameter pointing at: {veOcean.token}"
    )


# ========================================================================
@enforce_types
def do_newVeAllocate():
    HELP = """Generate new veAllocate (for testing)

Usage: dftool newVeAllocate CHAINID
"""
    if len(sys.argv) not in [3]:
        print(HELP)
        sys.exit(1)

    # extract inputs
    assert sys.argv[1] == "newVeAllocate"
    CHAINID = int(sys.argv[2])
    print(f"Arguments:\n CHAINID={CHAINID}")

    # main work
    networkutil.connect(CHAINID)
    from_account = _getPrivateAccount()
    contract = B.veAllocate.deploy({"from": from_account})
    print(f"veAllocate contract deployed at: {contract.address}")


# ========================================================================
@enforce_types
def do_veSetAllocation():
    HELP = """Allocate weight to veAllocate contract (for testing).
    Set to 0 to trigger resetAllocation event.

Usage: dftool veSetAllocation CHAINID amount exchangeId
"""
    if len(sys.argv) not in [5]:
        print(HELP)
        sys.exit(1)

    # extract inputs
    assert sys.argv[1] == "veSetAllocation"
    CHAINID = int(sys.argv[2])
    print(f"Arguments:\n CHAINID={CHAINID}")

    amount = float(sys.argv[3])
    print(f"Arguments:\n amount={amount}")

    exchangeId = str(sys.argv[4])
    print(f"Arguments:\n exchangeId={exchangeId}")

    # main work
    networkutil.connect(CHAINID)
    ADDRESS_FILE = os.environ.get("ADDRESS_FILE")
    if ADDRESS_FILE is not None:
        recordDeployedContracts(ADDRESS_FILE)
        from_account = _getPrivateAccount()
        veAllocate().setAllocation(amount, exchangeId, {"from": from_account})
        allocation = veAllocate().getTotalAllocation(from_account, 100, 0)
        votingPower = functools.reduce(lambda a, b: a + b, allocation[1])
        print(f"veAllocate voting power is: {votingPower}")


# ========================================================================
@enforce_types
def do_acctinfo():
    HELP = f"""Info about an account

Usage: dftool acctinfo CHAINID ACCOUNT_ADDR [TOKEN_ADDR]
  CHAINID -- {CHAINID_EXAMPLES}
  ACCOUNT_ADDR -- e.g. '0x987...' or '4'. If the latter, uses accounts[i]
  TOKEN_ADDR -- e.g. '0x123..'

If envvar ADDRESS_FILE is not None, it gives balance for OCEAN token too.
"""
    if len(sys.argv) not in [4, 5]:
        print(HELP)
        sys.exit(1)

    # extract inputs
    assert sys.argv[1] == "acctinfo"
    CHAINID = int(sys.argv[2])
    ACCOUNT_ADDR = sys.argv[3]
    TOKEN_ADDR = sys.argv[4] if len(sys.argv) >= 5 else None

    # do work
    print("Account info:")
    networkutil.connect(CHAINID)
    if len(str(ACCOUNT_ADDR)) == 1:
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
    HELP = f"""Info about a network

Usage: dftool chaininfo CHAINID
  CHAINID -- {CHAINID_EXAMPLES}
"""
    if len(sys.argv) not in [3]:
        print(HELP)
        sys.exit(1)

    # extract inputs
    assert sys.argv[1] == "chaininfo"
    CHAINID = int(sys.argv[2])

    # do work
    networkutil.connect(CHAINID)
    # blocks = len(brownie.network.chain)
    print("\nChain info:")
    print(f"  # blocks: {len(brownie.network.chain)}")


# ========================================================================
@enforce_types
def do_dispense_passive():
    HELP = f"""Dispense passive rewards

Usage: dftool dispense_passive CHAINID AMOUNT [ST]
    CHAINID -- {CHAINID_EXAMPLES}
    AMOUNT -- total amount of TOKEN to distribute (decimal, not wei)
    ST -- week start date -- YYYY-MM-DD
"""
    if len(sys.argv) not in [4, 5]:
        print(HELP)
        sys.exit(1)

    CHAINID = int(sys.argv[2])
    networkutil.connect(CHAINID)
    AMOUNT = float(sys.argv[3])
    ADDRESS_FILE = _getAddressEnvvarOrExit()
    recordDeployedContracts(ADDRESS_FILE)

    if AMOUNT == 0:
        START_DATE = datetime.datetime.strptime(sys.argv[4], "%Y-%m-%d")
        AMOUNT = getActiveRewardAmountForWeekEth(START_DATE)

    feedist = FeeDistributor()
    OCEAN = OCEANtoken()
    retryFunction(dispense.dispense_passive, 3, 60, OCEAN, feedist, AMOUNT)

    print("Dispensed passive rewards")


# ========================================================================
@enforce_types
def do_calculate_passive():
    HELP = f"""Calculate passive rewards

Usage: dftool calculate_passive CHAINID DATE CSV_DIR
    CHAINID -- {CHAINID_EXAMPLES}
    DATE -- date in format YYYY-MM-DD
    CSV_DIR -- output dir for passive-CHAINID.csv
"""
    if len(sys.argv) not in [5]:
        print(HELP)
        sys.exit(1)

    CHAINID = int(sys.argv[2])
    networkutil.connect(CHAINID)
    DATE = sys.argv[3]
    CSV_DIR = sys.argv[4]
    timestamp = int(timestrToTimestamp(DATE))
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
    HELP = f"""Checkpoint FeeDistributor contract

Usage: dftool checkpoint_feedist CHAINID
    CHAINID -- {CHAINID_EXAMPLES}
"""
    if len(sys.argv) not in [3]:
        print(HELP)
        sys.exit(1)

    CHAINID = int(sys.argv[2])
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


def _createDirIfNeeded(dir_: str):
    if not os.path.exists(dir_):
        print(f"Directory {dir_} did not exist, so created it")
        os.mkdir(dir_)


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
    if len(sys.argv) == 1:
        do_help_short(1)
        return

    func_name = f"do_{sys.argv[1]}"
    func = globals().get(func_name)
    if func is None:
        do_help_long(1)
        return

    func()
