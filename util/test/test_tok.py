from enforce_typing import enforce_types
import pytest

from util.tok import Tok

@enforce_types
def test_happy():
    tok = Tok(1, "0x12ab3", "OCEAN")

@enforce_types
def test_types():
    with pytest.raises(AssertionError):
        tok = Tok("not an int", "0x12ab3", "OCEAN")
        
    with pytest.raises(AssertionError):
        tok = Tok(1, 100, "OCEAN")
        
    with pytest.raises(AssertionError):
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
        
        
        
