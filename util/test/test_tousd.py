from enforce_typing import enforce_types

from util import tok
from util.tousd import stakesToUsd, poolvolsToUsd

# for shorter lines
RATES = {"OCEAN": 0.5, "H2O": 1.6, "UNAPP": 42.0}
C1, C2 = 7, 137
PA, PB, PC = "0xpoola_addr", "0xpoolb_addr", "0xpoolc_addr"
LP1, LP2, LP3, LP4 = "0xlp1_addr", "0xlp2_addr", "0xlp3_addr", "0xlp4_addr"
OCN_SYMB, H2O_SYMB, UNAPP_SYMB = "OCEAN", "H2O", "UNAPP"
OCN_ADDR, H2O_ADDR, UNAPP_ADDR = "0xocean", "0xh2o", "0xunapp"

APPROVED_TOKENS = tok.TokSet(
    [
        (C1, OCN_ADDR, OCN_SYMB),
        (C1, H2O_ADDR, H2O_SYMB),
        (C2, OCN_ADDR, OCN_SYMB),
        (C2, H2O_ADDR, H2O_SYMB),
    ]
)
TOK_SET = APPROVED_TOKENS


@enforce_types
def test_stakesToUsd_onebasetoken():
    stakes = {C1: {OCN_ADDR: {PA: {LP1: 3.0, LP2: 4.0}}}}
    stakes_USD = stakesToUsd(stakes, RATES, TOK_SET)
    assert stakes_USD == {C1: {PA: {LP1: 3.0 * 0.5, LP2: 4.0 * 0.5}}}


@enforce_types
def test_stakesToUsd_twobasetokens():
    stakes = {
        C1: {
            OCN_ADDR: {PA: {LP1: 3.0, LP2: 4.0}},
            H2O_ADDR: {PC: {LP1: 5.0, LP4: 6.0}},
        }
    }
    stakes_USD = stakesToUsd(stakes, RATES, TOK_SET)
    assert stakes_USD == {
        C1: {
            PA: {LP1: 3.0 * 0.5, LP2: 4.0 * 0.5},
            PC: {LP1: 5.0 * 1.6, LP4: 6.0 * 1.6},
        }
    }


@enforce_types
def test_poolvolsToUsd_onebasetoken():
    poolvols = {C1: {OCN_ADDR: {PA: 9.0, PB: 11.0}}}
    poolvols_USD = poolvolsToUsd(poolvols, RATES, TOK_SET)
    assert poolvols_USD == {C1: {PA: 9.0 * 0.5, PB: 11.0 * 0.5}}


@enforce_types
def test_poolvolsToUsd_twobasetokens():
    poolvols = {C1: {OCN_ADDR: {PA: 9.0, PB: 11.0}, H2O_ADDR: {PC: 13.0}}}
    poolvols_USD = poolvolsToUsd(poolvols, RATES, TOK_SET)
    assert poolvols_USD == {
        C1: {
            PA: 9.0 * 0.5,
            PB: 11.0 * 0.5,
            PC: 13.0 * 1.6,
        }
    }
