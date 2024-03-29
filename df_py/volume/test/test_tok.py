import pytest
from enforce_typing import enforce_types

from df_py.volume.models import Tok, TokSet


@enforce_types
def test_happy():
    Tok(1, "0x12ab3", "OCEAN")


@enforce_types
def test_types():
    with pytest.raises(TypeError):
        Tok("not an int", "0x12ab3", "OCEAN")

    with pytest.raises(TypeError):
        Tok(1, 100, "OCEAN")

    with pytest.raises(TypeError):
        Tok(1, "0x12ab3", 322)


@enforce_types
def test_casing():
    with pytest.raises(AssertionError):
        Tok(1, "0x12Ab3", "OCEAN")

    with pytest.raises(AssertionError):
        Tok(1, "0x12ab3", "OcEaN")


@enforce_types
def test_0x():
    with pytest.raises(AssertionError):
        Tok(1, "12ab3", "OCEAN")


@enforce_types
def test_TokSet_empty_init():
    tok_set = TokSet()
    assert len(tok_set.toks) == 0

    tok_set = TokSet([])
    assert len(tok_set.toks) == 0


@enforce_types
def test_TokSet_main():
    tok_set = TokSet([(1, "0x123", "OCEAN"), (1, "0x456", "H2O")])
    tok_set.add(2, "0x78b", "OCEAN")

    assert tok_set.has_chain(1)
    assert tok_set.has_chain(2)
    assert not tok_set.has_chain(9)

    assert tok_set.has_address(1, "0x123")
    assert tok_set.has_address(2, "0x78b")
    assert not tok_set.has_address(9, "0x78b")
    with pytest.raises(AssertionError):
        tok_set.has_address(1, "123")  # missing "0x"
    with pytest.raises(AssertionError):
        tok_set.has_address(2, "0x78B")  # unwanted uppercase in address

    assert tok_set.has_symbol(1, "OCEAN")
    assert tok_set.has_symbol(1, "H2O")
    assert not tok_set.has_symbol(9, "OCEAN")
    with pytest.raises(AssertionError):
        tok_set.has_address(1, "ocEaN")  # unwanted lowercase in address

    assert tok_set.get_symbol(1, "0x123") == "OCEAN"
    assert tok_set.get_symbol(1, "0x456") == "H2O"
    with pytest.raises(AssertionError):
        tok_set.get_symbol(2, "0x78B")  # unwanted uppercase in address
    with pytest.raises(AssertionError):
        tok_set.get_symbol(9, "0x78b")  # only query what tokens exist

    assert tok_set.getAddress(1, "OCEAN") == "0x123"
    assert tok_set.getAddress(2, "OCEAN") == "0x78b"  # diff't address on diff't chain
    assert tok_set.getAddress(1, "H2O") == "0x456"
    with pytest.raises(AssertionError):
        tok_set.getAddress(9, "OCEAN")  # only query what tokens exist
    with pytest.raises(AssertionError):
        tok_set.getAddress(1, "ocEaN")  # unwanted lowercase in symbol

    tok = tok_set.tok_at_address(1, "0x123")
    assert tok.chainID == 1
    assert tok.address == "0x123"
    assert tok.symbol == "OCEAN"
    assert tok_set.tok_at_address(1, "0xfoo") is None
    with pytest.raises(AssertionError):
        tok_set.tok_at_address(2, "0x78B")  # unwanted uppercase in symbol

    tok = tok_set.tok_at_symbol(1, "OCEAN")
    assert tok.chainID == 1
    assert tok.address == "0x123"
    assert tok.symbol == "OCEAN"
    assert tok_set.tok_at_symbol(1, "FOO") is None
    with pytest.raises(AssertionError):
        tok_set.tok_at_symbol(1, "oCeAn")  # unwanted lowercase in symbol

    addrs = tok_set.export_token_addrs()
    assert sorted(addrs.keys()) == [1, 2]
    assert sorted(addrs[1]) == ["0x123", "0x456"]
    assert sorted(addrs[2]) == ["0x78b"]
