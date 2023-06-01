# pylint: disable=too-many-lines,too-many-statements
import datetime
import functools
import os
import sys

import brownie
from enforce_typing import enforce_types
from web3.middleware import geth_poa_middleware

from util import (
    allocations,
    blockrange,
    calcrewards,
    constants,
    csvs,
    dispense,
    getrate,
    networkutil,
    query,
)
from util.base18 import from_wei
from util.blocktime import getfinBlock, timestrToTimestamp
from util.calcrewards import calcRewards
from util.challenge import judge
from util.constants import BROWNIE_PROJECT as B
from util.multisig import send_multisig_tx
from util.networkutil import DEV_CHAINID, chainIdToMultisigAddr
from util.oceantestutil import (
    randomConsumeFREs,
    randomCreateDataNFTWithFREs,
    randomLockAndAllocate,
)
from util.oceanutil import (
    FeeDistributor,
    OCEANtoken,
    recordDeployedContracts,
    veAllocate,
)
from util.retry import retryFunction
from util.vesting_schedule import getActiveRewardAmountForWeekEth

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
  dftool predictoor_data CSV_DIR CHAINID [RETRIES]
  dftool calc CSV_DIR TOT_OCEAN [START_DATE] [IGNORED] - from stakes/etc csvs, output rewards csvs across Volume + Challenge + Predictoor DF
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

    # brownie setup
    networkutil.connect(CHAINID)
    chain = brownie.network.chain
    recordDeployedContracts(ADDRESS_FILE)

    # main work
    rng = blockrange.create_range(chain, ST, FIN, NSAMP, SECRET_SEED)
    (Vi, Ci, SYMi) = retryFunction(
        query.queryVolsOwnersSymbols, RETRIES, 10, rng, CHAINID
    )
    csvs.saveNftvolsCsv(Vi, CSV_DIR, CHAINID)
    csvs.saveOwnersCsv(Ci, CSV_DIR, CHAINID)
    csvs.saveSymbolsCsv(SYMi, CSV_DIR, CHAINID)

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
    # -query.queryNftinfo() can be problematic; it's only used for frontend data
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
    nftinfo = retryFunction(query.queryNftinfo, RETRIES, DELAY_S, CHAINID, ENDBLOCK)
    csvs.saveNftinfoCsv(nftinfo, CSV_DIR, CHAINID)

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
    _exitIfFileExists(csvs.allocationCsvFilename(CSV_DIR, NSAMP > 1))

    # brownie setup
    networkutil.connect(CHAINID)
    chain = brownie.network.chain

    # main work
    rng = blockrange.create_range(chain, ST, FIN, NSAMP, SECRET_SEED)
    allocs = retryFunction(query.queryAllocations, RETRIES, 10, rng, CHAINID)
    csvs.saveAllocationCsv(allocs, CSV_DIR, NSAMP > 1)

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
    _exitIfFileExists(csvs.vebalsCsvFilename(CSV_DIR, NSAMP > 1))

    # brownie setup
    networkutil.connect(CHAINID)
    chain = brownie.network.chain
    rng = blockrange.create_range(chain, ST, FIN, NSAMP, SECRET_SEED)

    balances, locked_amt, unlock_time = retryFunction(
        query.queryVebalances, RETRIES, 10, rng, CHAINID
    )
    csvs.saveVebalsCsv(balances, locked_amt, unlock_time, CSV_DIR, NSAMP > 1)

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
    _exitIfFileExists(csvs.rateCsvFilename(TOKEN_SYMBOL, CSV_DIR))
    _createDirIfNeeded(CSV_DIR)

    # main work
    rate = retryFunction(getrate.getrate, RETRIES, 60, TOKEN_SYMBOL, ST, FIN)
    print(f"rate = ${rate:.4f} / {TOKEN_SYMBOL}")
    csvs.saveRateCsv(TOKEN_SYMBOL, rate, CSV_DIR)

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

    csvs.saveChallengeDataCsv(challenge_data, CSV_DIR)

    print("dftool challenge_data: Done")


# ========================================================================
@enforce_types
def do_predictoor_data():
    HELP = f"""Get data for Predictoor DF

Usage: dftool predictoor_data CSV_DIR CHAINID [RETRIES]
  CSV_DIR -- output directory for rate-TOKEN_SYMBOL.csv file
  CHAINID -- {CHAINID_EXAMPLES}
  RETRIES -- # times to retry failed queries
"""
    if len(sys.argv) not in [2 + 3, 2 + 4]:
        print(HELP)
        sys.exit(1)

    # extract inputs
    assert sys.argv[1] == "predictoor_data"
    CSV_DIR = sys.argv[2]
    CHAINID = int(sys.argv[3])
    RETRIES = 1 if len(sys.argv) == 4 else int(sys.argv[4])
    print("dftool predictoor_data: Begin")
    print(
        f"Arguments: "
        f"\n CSV_DIR={CSV_DIR}"
        f"\n CHAINID={CHAINID}"
        f"\n RETRIES={RETRIES}"
    )

    # extract envvars
    ADDRESS_FILE = _getAddressEnvvarOrExit()
    SECRET_SEED = _getSecretSeedOrExit()  # pylint: disable=unused-variable

    # check files, prep dir
    if not os.path.exists(CSV_DIR):
        print(f"\nDirectory {CSV_DIR} doesn't exist; nor do rates. Exiting.")
        sys.exit(1)

    # brownie setup
    networkutil.connect(CHAINID)
    chain = brownie.network.chain  # pylint: disable=unused-variable
    recordDeployedContracts(ADDRESS_FILE)

    # main work
    predictoor_data = retryFunction(
        query.queryPredictoor_Data,
        RETRIES,
        CHAINID,
    )
    csvs.savePredictoor_Data(predictoor_data, CSV_DIR, CHAINID)

    print("dftool predictoor_data: Done")


# ========================================================================
@enforce_types
def do_calc():
    HELP = """from stakes/etc csvs, output rewards csvs across Volume + Challenge + Predictoor DF

Usage: dftool calc CSV_DIR TOT_OCEAN [START_DATE] [IGNORED]
  CSV_DIR -- directory: input csvs (stakes, vols, etc), output rewards.csv
  TOT_OCEAN -- total amount of TOKEN to distribute (decimal, not wei)
  START_DATE -- week start date -- YYYY-MM-DD. Used when TOT_OCEAN == 0
  IGNORED -- Ignored. Kept here for compatibility.
"""
    if len(sys.argv) not in [4, 5, 6]:
        print(HELP)
        sys.exit(1)

    # extract inputs
    assert sys.argv[1] == "calc"
    CSV_DIR = sys.argv[2]
    TOT_OCEAN = float(sys.argv[3])
    START_DATE = None if len(sys.argv) == 4 else sys.argv[4]

    print("dftool calc: Begin")
    print(
        f"Arguments: "
        f"\n CSV_DIR={CSV_DIR}"
        f"\n TOT_OCEAN={TOT_OCEAN}"
        f"\n START_DATE={START_DATE}"
        "\n"
    )

    # condition inputs
    if TOT_OCEAN == 0 and START_DATE is None:
        print("TOT_OCEAN == 0, so must give a start date. Exiting.")
        sys.exit(1)

    if TOT_OCEAN == 0:
        START_DATE = datetime.datetime.strptime(START_DATE, "%Y-%m-%d")
        TOT_OCEAN = getActiveRewardAmountForWeekEth(START_DATE)
        print(
            f"TOT_OCEAN was 0, so re-calc'd: TOT_OCEAN={TOT_OCEAN}"
            f", START_DATE={START_DATE}"
        )
    elif START_DATE is not None:
        print("TOT_OCEAN was nonzero, so re-calc'd: START_DATE=None")
        START_DATE = None

    # do we have the input files?
    alloc_fname = csvs.allocationCsvFilename(CSV_DIR)  # need for loadStakes()
    if not os.path.exists(alloc_fname):
        print(f"\nNo file {alloc_fname} in '{CSV_DIR}'. Exiting.")
        sys.exit(1)

    vebals_fname = csvs.vebalsCsvFilename(CSV_DIR)  # need for loadStakes()
    if not os.path.exists(vebals_fname):
        print(f"\nNo file {vebals_fname} in '{CSV_DIR}'. Exiting.")
        sys.exit(1)

    if not csvs.nftvolsCsvFilenames(CSV_DIR):
        print(f"\nNo 'nftvols*.csv' files in '{CSV_DIR}'. Exiting.")
        sys.exit(1)

    if not csvs.ownersCsvFilenames(CSV_DIR):
        print(f"\nNo 'owners*.csv' files in '{CSV_DIR}'. Exiting.")
        sys.exit(1)

    if not csvs.symbolsCsvFilenames(CSV_DIR):
        print(f"\nNo 'symbols*.csv' files in '{CSV_DIR}'. Exiting.")
        sys.exit(1)

    if not csvs.rateCsvFilenames(CSV_DIR):
        print(f"\nNo 'rate*.csv' files in '{CSV_DIR}'. Exiting.")
        sys.exit(1)

    # shouldn't already have the output file
    _exitIfFileExists(csvs.rewardsperlpCsvFilename(CSV_DIR, "OCEAN"))
    _exitIfFileExists(csvs.rewardsinfoCsvFilename(CSV_DIR, "OCEAN"))

    # brownie setup
    networkutil.connect(5)
    ADDRESS_FILE = _getAddressEnvvarOrExit()
    recordDeployedContracts(ADDRESS_FILE)

    # main work
    S = allocations.loadStakes(CSV_DIR)
    V = csvs.loadNftvolsCsvs(CSV_DIR)
    C = csvs.loadOwnersCsvs(CSV_DIR)
    SYM = csvs.loadSymbolsCsvs(CSV_DIR)
    R = csvs.loadRateCsvs(CSV_DIR)
    do_pubrewards = constants.DO_PUBREWARDS
    do_rank = constants.DO_RANK

    prev_week = 0
    if START_DATE is None:
        cur_week = calcrewards.getDfWeekNumber(datetime.datetime.now())
        prev_week = cur_week - 1
    else:
        prev_week = calcrewards.getDfWeekNumber(START_DATE)
    m = calcrewards.calcDcvMultiplier(prev_week)
    print(f"Given prev_week=DF{prev_week}, then DCV_multiplier={m}")

    rewperlp, rewinfo = calcRewards(
        S, V, C, SYM, R, m, TOT_OCEAN, do_pubrewards, do_rank
    )

    csvs.saveRewardsperlpCsv(rewperlp, CSV_DIR, "OCEAN")
    csvs.saveRewardsinfoCsv(rewinfo, CSV_DIR, "OCEAN")

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
    rewards = csvs.loadRewardsCsv(CSV_DIR, token_symbol)

    # "flatten" the rewards dict to dispense all chains in one go
    all_rewards = calcrewards.flattenRewards(rewards)

    # dispense
    dispense.dispense(
        all_rewards,
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

    from util import oceantestutil  # pylint: disable=import-outside-toplevel

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
    passive_fname = csvs.passiveCsvFilename(CSV_DIR)
    vebals_realtime_fname = csvs.vebalsCsvFilename(CSV_DIR, False)
    if not os.path.exists(vebals_realtime_fname):
        print(f"\nNo file {vebals_realtime_fname} in '{CSV_DIR}'. Exiting.")
        sys.exit(1)
    _exitIfFileExists(passive_fname)

    # get addresses
    vebals, _, _ = csvs.loadVebalsCsv(CSV_DIR, False)
    addresses = list(vebals.keys())

    balances, rewards = query.queryPassiveRewards(timestamp, addresses)

    # save to csv
    csvs.savePassiveCsv(rewards, balances, CSV_DIR)


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
