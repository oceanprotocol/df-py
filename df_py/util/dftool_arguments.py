# pylint: disable=too-many-lines,too-many-statements
import argparse
import datetime
import os
import sys
from typing import Optional

from enforce_typing import enforce_types

from df_py.challenge import judge
from df_py.util.networkutil import DEV_CHAINID, chain_id_to_rpc_url

CHAINID_EXAMPLES = (
    f"{DEV_CHAINID} for development, 1 for (eth) mainnet, 137 for polygon"
)

# ========================================================================
HELP_LONG = """Data Farming tool, for use by OPF.

Usage: dftool get_rate|volsym|allocations.. ARG1 ARG2 ..

  dftool help - full command list

  dftool get_rate TOKEN_SYMBOL ST FIN CSV_DIR --RETRIES
  dftool volsym ST FIN NSAMP CSV_DIR CHAINID --RETRIES - query chain, output volumes, symbols, owners
  dftool allocations ST FIN NSAMP CSV_DIR CHAINID --RETRIES
  dftool vebals ST FIN NSAMP CSV_DIR CHAINID --RETRIES
  dftool challenge_data CSV_DIR [DEADLINE] --RETRIES
  dftool predictoor_data CSV_DIR START_DATE END_DATE CHAINID --RETRIES
  dftool calc volume|predictoor|challenge CSV_DIR TOT_OCEAN START_DATE - from stakes/etc csvs (or predictoor/challenge data csvs), output rewards
  dftool dispense_active CSV_DIR CHAINID --DFREWARDS_ADDR --TOKEN_ADDR --BATCH_NBR - from rewards, dispense funds
  dftool dispense_passive CHAINID AMOUNT
  dftool nftinfo CSV_DIR CHAINID -- Query chain, output nft info csv

  dftool new_acct - generate new account
  dftool init_dev_wallets CHAINID - Init wallets with OCEAN. (GANACHE ONLY)
  dftool new_token CHAINID - generate new token (for testing)
  dftool acct_info CHAINID ACCOUNT_ADDR [TOKEN_ADDR] - info about an account
  dftool chain_info CHAINID - info about a network

  dftool mine TIMEDELTA - force chain to pass time (ganache only)

  dftool new_veocean CHAINID TOKEN_ADDR - deploy veOcean using TOKEN_ADDR (for testing)
  dftool new_veallocate CHAINID - deploy veAllocate (for testing)
  dftool ve_set_allocation CHAINID amount TOKEN_ADDR - Allocate weight to veAllocate contract. Set to 0 to reset. (for testing)

  dftool many_random CHAINID - deploy many datatokens + locks OCEAN + allocates + consumes (for testing)
  dftool new_df_rewards CHAINID - deploy new DFRewards contract
  dftool new_df_strategy CHAINID DFREWARDS_ADDR DFSTRATEGY_NAME - deploy new DFStrategy
  dftool add_strategy CHAINID DFREWARDS_ADDR DFSTRATEGY_ADDR - Add a strategy to DFRewards contract
  dftool retire_strategy CHAINID DFREWARDS_ADDR DFSTRATEGY_ADDR - Retire a strategy from DFRewards contract
  dftool checkpoint_feedist CHAINID - checkpoint FeeDistributor contract
  dftool dummy_csvs SUBSTREAM CSV_DIR

Transactions are signed with envvar 'DFTOOL_KEY`.
"""


@enforce_types
def do_help_long(status_code=0):
    print(HELP_LONG)
    sys.exit(status_code)


@enforce_types
def valid_date_and_convert(s: str):
    try:
        return datetime.datetime.strptime(s, "%Y-%m-%d")
    except ValueError:
        pass

    msg = "not a valid date: {s}"
    raise argparse.ArgumentTypeError(msg)


@enforce_types
def chain_type(s: str):
    if not s.isnumeric():
        raise argparse.ArgumentTypeError("CHAINID must be an integer")

    try:
        chain_id_to_rpc_url(int(s))

        return int(s)
    except ValueError as e:
        raise argparse.ArgumentTypeError(str(e)) from e


@enforce_types
def valid_date(s: str):
    try:
        datetime.datetime.strptime(s, "%Y-%m-%d")
        return s
    except ValueError:
        pass

    msg = "not a valid date: {s}"
    raise argparse.ArgumentTypeError(msg)


@enforce_types
def block_or_valid_date(s: str):
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

    msg = f"not a valid date or block number: {s}"
    raise argparse.ArgumentTypeError(msg)


@enforce_types
def existing_path(s: str):
    if not os.path.exists(s):
        msg = f"Directory {s} doesn't exist."
        raise argparse.ArgumentTypeError(msg)

    return s


@enforce_types
def autocreate_path(s: str):
    if not os.path.exists(s):
        print(f"Directory {s} did not exist, so created it")
        os.mkdir(s)

    return s


@enforce_types
def challenge_date(s: str):
    if s == "None":
        return None

    try:
        judge.parse_deadline_str(s)
        return s
    except Exception as e:  # pylint: disable=bare-except
        raise argparse.ArgumentTypeError(str(e)) from e


@enforce_types
def print_arguments(arguments: argparse.Namespace):
    arguments_dict = arguments.__dict__
    command = arguments_dict.pop("command", None)

    print(f"dftool {command}: Begin")
    print("Arguments:")

    for arg_k, arg_v in arguments_dict.items():
        print(f"{arg_k}={arg_v}")


@enforce_types
class StartFinArgumentParser(argparse.ArgumentParser):
    @enforce_types
    def __init__(
        self, description: str, epilog: str, command_name: str, csv_names: str
    ):
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
        self.add_argument("CHAINID", type=chain_type, help=CHAINID_EXAMPLES)
        self.add_argument(
            "--RETRIES",
            default=1,
            type=int,
            help="# times to retry failed queries",
            required=False,
        )


@enforce_types
class SimpleChainIdArgumentParser(argparse.ArgumentParser):
    @enforce_types
    def __init__(
        self, description: str, command_name: str, epilog: Optional[str] = None
    ):
        super().__init__(
            description=description,
            formatter_class=argparse.RawDescriptionHelpFormatter,
            epilog=epilog,
        )
        self.add_argument("command", choices=[command_name])
        self.add_argument("CHAINID", type=chain_type, help=CHAINID_EXAMPLES)

    @enforce_types
    def print_args_and_get_chain(self) -> int:
        arguments = self.parse_args()
        print_arguments(arguments)

        return arguments.CHAINID


@enforce_types
class DfStrategyArgumentParser(argparse.ArgumentParser):
    @enforce_types
    def __init__(self, description: str, command_name: str):
        super().__init__(description=description)
        self.add_argument("command", choices=[command_name])
        self.add_argument("CHAINID", type=chain_type, help=CHAINID_EXAMPLES)
        self.add_argument("DFREWARDS_ADDR", type=str, help="DFRewards contract address")
        self.add_argument(
            "DFSTRATEGY_ADDR", type=str, help="DFStrategy contract address"
        )
