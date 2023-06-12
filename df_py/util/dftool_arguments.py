# pylint: disable=too-many-lines,too-many-statements
import argparse
import datetime
import os
import sys

from enforce_typing import enforce_types

from df_py.challenge import judge
from df_py.util.networkutil import DEV_CHAINID

CHAINID_EXAMPLES = (
    f"{DEV_CHAINID} for development, 1 for (eth) mainnet, 137 for polygon"
)

# ========================================================================
HELP_SHORT = """Data Farming tool, for use by OPF.

Usage: dftool compile|getrate|volsym|.. ARG1 ARG2 ..

  dftool help - full command list

  dftool compile - compile contracts
  dftool getrate TOKEN_SYMBOL ST FIN CSV_DIR --RETRIES
  dftool volsym ST FIN NSAMP CSV_DIR CHAINID --RETRIES - query chain, output volumes, symbols, owners
  dftool allocations ST FIN NSAMP CSV_DIR CHAINID --RETRIES
  dftool vebals ST FIN NSAMP CSV_DIR CHAINID --RETRIES
  dftool challenge_data CSV_DIR [DEADLINE] --RETRIES
  dftool predictoor_data CSV_DIR START_DATE END_DATE CHAINID --RETRIES
  dftool calc CSV_DIR TOT_OCEAN [START_DATE] [IGNORED] - from stakes/etc csvs, output rewards csvs across Volume + Challenge + Predictoor DF
  dftool dispense_active CSV_DIR CHAINID --DFREWARDS_ADDR --TOKEN_ADDR --BATCH_NBR - from rewards, dispense funds
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

  dftool mine BLOCKS --TIMEDELTA - force chain to pass time (ganache only)

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
def do_help_short(status_code=0):
    print(HELP_SHORT)
    sys.exit(status_code)


@enforce_types
def do_help_long(status_code=0):
    print(HELP_LONG)
    sys.exit(status_code)


def valid_date_and_convert(s):
    try:
        return datetime.datetime.strptime(s, "%Y-%m-%d")
    except ValueError:
        pass

    msg = "not a valid date: {s}"
    raise argparse.ArgumentTypeError(msg)


def valid_date(s):
    try:
        datetime.datetime.strptime(s, "%Y-%m-%d")
        return s
    except ValueError:
        pass

    msg = "not a valid date: {s}"
    raise argparse.ArgumentTypeError(msg)


def block_or_valid_date(s):
    if s == "latest":
        return s

    try:
        return int(s)
    except ValueError:
        pass

    try:
        datetime.datetime.strptime(s, "%Y-%m-%d")
        return s
    except ValueError:
        pass

    try:
        datetime.datetime.strptime(s, "%Y-%m-%d_%H:%M")
        return s
    except ValueError:
        pass

    msg = "not a valid date or block number: {s}"
    raise argparse.ArgumentTypeError(msg)


def existing_path(s):
    if not os.path.exists(s):
        msg = f"Directory {s} doesn't exist."
        raise argparse.ArgumentTypeError(msg)

    return s


def autocreate_path(s):
    if not os.path.exists(s):
        print(f"Directory {s} did not exist, so created it")
        os.mkdir(s)

    return s


def challenge_date(s):
    if s == "None":
        return None

    try:
        judge.parse_deadline_str(s)
        return s
    except Exception as e:  # pylint: disable=bare-except
        raise argparse.ArgumentTypeError(str(e)) from e


def print_arguments(arguments):
    arguments_dict = arguments.__dict__
    command = arguments_dict.pop("command", None)

    print(f"dftool {command}: Begin")
    print("Arguments:")

    for arg_k, arg_v in arguments_dict.items():
        print(f"{arg_k}={arg_v}")


class StartFinArgumentParser(argparse.ArgumentParser):
    def __init__(self, description, epilog, command_name, csv_names):
        super().__init__(
            description=description,
            formatter_class=argparse.RawDescriptionHelpFormatter,
            epilog=epilog,
        )
        self.add_argument("command", choices=[command_name])
        self.add_argument(
            "ST",
            type=block_or_valid_date,
            help="first block # to calc on | YYYY-MM-DD | YYYY-MM-DD_HH:MM",
        )
        self.add_argument(
            "FIN",
            type=block_or_valid_date,
            help="last block # to calc on | YYYY-MM-DD | YYYY-MM-DD_HH:MM | latest",
        )
        self.add_argument(
            "NSAMP",
            type=int,
            help="blocks to sample liquidity from, from blocks [ST, ST+1, .., FIN]",
        )
        self.add_argument(
            "CSV_DIR",
            type=existing_path,
            help=f"output dir for {csv_names}",
        )
        self.add_argument("CHAINID", type=int, help=CHAINID_EXAMPLES)
        self.add_argument(
            "--RETRIES",
            default=1,
            type=int,
            help="# times to retry failed queries",
            required=False,
        )


class SimpleChainIdArgumentParser(argparse.ArgumentParser):
    def __init__(self, description, command_name, epilog=None):
        super().__init__(
            description=description,
            formatter_class=argparse.RawDescriptionHelpFormatter,
            epilog=epilog,
        )
        self.add_argument("command", choices=[command_name])
        self.add_argument("CHAINID", type=int, help=CHAINID_EXAMPLES)

    def print_args_and_get_chain(self):
        arguments = self.parse_args()
        print_arguments(arguments)

        return arguments.CHAINID


class DfStrategyArgumentParser(argparse.ArgumentParser):
    def __init__(self, description, command_name):
        super().__init__(description=description)
        self.add_argument("command", choices=[command_name])
        self.add_argument("CHAINID", type=int, help=CHAINID_EXAMPLES)
        self.add_argument("DFREWARDS_ADDR", type=str, help="DFRewards contract address")
        self.add_argument(
            "DFSTRATEGY_ADDR", type=str, help="DFStrategy contract address"
        )
