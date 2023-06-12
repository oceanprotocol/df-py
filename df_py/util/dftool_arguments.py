import argparse
import datetime
import os


# All these functions already exist in the arguments branch.
# When fixing conflicts, just delete these functions without mercy.
def valid_date_and_convert(s):
    try:
        return datetime.datetime.strptime(s, "%Y-%m-%d")
    except ValueError:
        pass

    msg = "not a valid date: {s}"
    raise argparse.ArgumentTypeError(msg)


def existing_path(s):
    if not os.path.exists(s):
        msg = f"Directory {s} doesn't exist."
        raise argparse.ArgumentTypeError(msg)

    return s


def print_arguments(arguments):
    arguments_dict = arguments.__dict__
    command = arguments_dict.pop("command", None)

    print(f"dftool {command}: Begin")
    print("Arguments:")

    for arg_k, arg_v in arguments_dict.items():
        print(f"{arg_k}={arg_v}")
