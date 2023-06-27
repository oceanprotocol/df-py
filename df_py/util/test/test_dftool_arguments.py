import argparse
from datetime import datetime

import pytest

from df_py.util.dftool_arguments import (
    autocreate_path,
    block_or_valid_date,
    existing_path,
    valid_date,
    valid_date_and_convert,
)


def test_valid_date_and_convert():
    assert isinstance(valid_date_and_convert("2020-01-01"), datetime)

    with pytest.raises(argparse.ArgumentTypeError, match="not a valid date"):
        valid_date_and_convert("a string")


def test_valid_date():
    assert valid_date("2020-01-01") == "2020-01-01"

    with pytest.raises(argparse.ArgumentTypeError, match="not a valid date"):
        valid_date("a string")


def test_block_or_valid_date():
    assert block_or_valid_date("latest") == "latest"
    assert block_or_valid_date("14") == 14
    assert block_or_valid_date("2020-01-01") == "2020-01-01"
    assert block_or_valid_date("2020-01-01_14:30") == "2020-01-01_14:30"

    with pytest.raises(argparse.ArgumentTypeError, match="not a valid date"):
        block_or_valid_date("a string")


def test_autocreate_path(tmp_path):
    path = tmp_path / "test"
    assert autocreate_path(str(path)) == str(path)
    assert path.exists()


def test_existing_path(tmp_path):
    path = tmp_path / "test"
    path.mkdir()
    assert existing_path(str(path)) == str(path)

    with pytest.raises(argparse.ArgumentTypeError, match="doesn't exist"):
        existing_path(str(tmp_path / "not_existing"))
