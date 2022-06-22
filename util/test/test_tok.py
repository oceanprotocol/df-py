from enforce_typing import enforce_types
import pytest

from util.tok import Tok, TokSet

@enforce_types
def test_happy():
    tok = Tok(1, "0x12ab3", "OCEAN")

@enforce_types
def test_types():
    with pytest.raises(TypeError):
        tok = Tok("not an int", "0x12ab3", "OCEAN")
        
    with pytest.raises(TypeError):
        tok = Tok(1, 100, "OCEAN")
        
    with pytest.raises(TypeError):
        tok = Tok(1, "0x12ab3", 322)
        
@enforce_types
def test_casing():
    with pytest.raises(AssertionError):
        tok = Tok(1, "0x12Ab3", "OCEAN")
        
    with pytest.raises(AssertionError):
        tok = Tok(1, "0x12ab3", "OcEaN")

@enforce_types
def test_0x():
    with pytest.raises(AssertionError):
        tok = Tok(1, "12ab3", "OCEAN")


@enforce_types
def test_TokSet():
    l = [Tok(1, "0x123", "OCEAN"),
         Tok(1, "0x456", "H2O"),
         Tok(2, "0x789", "OCEAN")]
    tok_set = TokSet(l)
    
    assert tok_set.hasAddress(1, "0x123")
    assert tok_set.hasAddress(2, "0x789")
    assert not tok_set.hasAddress(9, "0x789")
    
    assert tok_set.symbol(1, "0x123") == "OCEAN"
    assert tok_set.symbol(1, "0x456") == "H2O"
    with pytest.raises(AssertionError):
        tok_set.symbol(9, "0x789")

    tok = tok_set.tokAtAddress(1, "0x123")
    assert tok.chainID == 1
    assert tok.address == "0x123"
    assert tok.symbol == "OCEAN"
        
        
        
