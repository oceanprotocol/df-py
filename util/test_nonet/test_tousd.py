from enforce_typing import enforce_types
from util.networkutil import _CHAINID_TO_ADDRS

from util.tousd import ratesToAddrRates, nftvolsToUsd

# for shorter lines
RATES = {"OCEAN": 0.5, "H2O": 1.6, "UNAPP": 42.0}
C1, C2 = 7, 137
PA, PB, PC = "0xpoola_addr", "0xpoolb_addr", "0xpoolc_addr"
LP1, LP2, LP3, LP4 = "0xlp1_addr", "0xlp2_addr", "0xlp3_addr", "0xlp4_addr"
OCN_SYMB, H2O_SYMB, UNAPP_SYMB = "OCEAN", "H2O", "UNAPP"
OCN_ADDR, H2O_ADDR, UNAPP_ADDR = "0xocean", "0xh2o", "0xunapp"
SYMBOLS = {C1: {OCN_ADDR: OCN_SYMB, H2O_ADDR: H2O_SYMB}}


@enforce_types
def test_ratesToAddrRates_onechain_onetoken():
    rates = {"OCEAN": 0.5}
    symbols = {C1: {"0xOCEAN": "OCEAN"}}
    addr_rates = ratesToAddrRates(rates, symbols)
    assert addr_rates == {C1: {"0xOCEAN": 0.5}}


@enforce_types
def test_ratesToAddrRates_onechain_twotokens():
    rates = {"OCEAN": 0.5, "H2O": 1.6}
    symbols = {C1: {"0xOCEAN": "OCEAN", "0xH2O": "H2O"}}
    addr_rates = ratesToAddrRates(rates, symbols)
    assert addr_rates == {C1: {"0xOCEAN": 0.5, "0xH2O": 1.6}}


@enforce_types
def test_ratesToAddrRates_twochains_twotokens():
    rates = {"OCEAN": 0.5}
    symbols = {C1: {"0xOCEAN1": "OCEAN"}, C2: {"0xOCEAN2": "OCEAN"}}
    addr_rates = ratesToAddrRates(rates, symbols)
    assert addr_rates == {C1: {"0xOCEAN1": 0.5}, C2: {"0xOCEAN2": 0.5}}


@enforce_types
def test_ratesToAddrRates_extraneous_rate():
    rates = {"OCEAN": 0.5, "H2O": 1.6}  # H2O's here but not in symbols, so extraneous
    symbols = {C1: {"0xOCEAN": "OCEAN"}}
    addr_rates = ratesToAddrRates(rates, symbols)
    assert addr_rates == {C1: {"0xOCEAN": 0.5}}


@enforce_types
def test_ratesToAddrRates_extraneous_symbol():
    rates = {"OCEAN": 0.5}
    symbols = {
        C1: {"0xOCEAN": "OCEAN", "0xH2O": "H2O"}
    }  # H2O's here but not in rates, so extraneous
    addr_rates = ratesToAddrRates(rates, symbols)
    assert addr_rates == {C1: {"0xOCEAN": 0.5}}


@enforce_types
def test_ratesToAddrRates_symbol_changes_between_chains():
    # symbol on chain 2 is MOCEAN, not OCEAN!
    rates = {"OCEAN": 0.5}
    symbols = {C1: {"0xOCEAN1": "OCEAN"}, C2: {"0xOCEAN2": "MOCEAN"}}

    # the result: it simply won't have an entry for 0xOCEAN2
    addr_rates = ratesToAddrRates(rates, symbols)
    assert addr_rates == {C1: {"0xOCEAN1": 0.5}, C2: {}}

    # here's the intervention needed
    rates["MOCEAN"] = rates["OCEAN"]

    # now it will work
    addr_rates = ratesToAddrRates(rates, symbols)
    assert addr_rates == {
        C1: {"0xOCEAN1": 0.5},
        C2: {"0xOCEAN2": 0.5},
    }  # has entry for 0xOCEAN2


@enforce_types
def test_nftvolsToUsd_onebasetoken():
    poolvols = {C1: {OCN_ADDR: {PA: 9.0, PB: 11.0}}}
    poolvols_USD = nftvolsToUsd(poolvols, SYMBOLS, RATES)
    assert poolvols_USD == {C1: {PA: 9.0 * 0.5, PB: 11.0 * 0.5}}


@enforce_types
def test_nftvolsToUsd_twobasetokens():
    poolvols = {C1: {OCN_ADDR: {PA: 9.0, PB: 11.0}, H2O_ADDR: {PC: 13.0}}}
    poolvols_USD = nftvolsToUsd(poolvols, SYMBOLS, RATES)
    assert poolvols_USD == {
        C1: {
            PA: 9.0 * 0.5,
            PB: 11.0 * 0.5,
            PC: 13.0 * 1.6,
        }
    }


@enforce_types
def test_native_token_rates():
    base_token = _CHAINID_TO_ADDRS[1].lower()
    rates = {"ETH": 100.0}
    symbols = {1: {"x": "x"}}
    nftvols = {1: {base_token: {LP1.lower(): 1.0, LP2.lower(): 2.0}}}

    nftvols_USD = nftvolsToUsd(nftvols, symbols, rates)
    assert nftvols_USD == {1: {LP1: 100.0, LP2: 200.0}}
