from enforce_typing import enforce_types
import pytest
from pytest import approx

from df_py.challenge.nmse import calc_nmse, plot_prices


@enforce_types
def test_nmse1():
    # values taken from Predict-ETH round 7, see https://rb.gy/2bzw9
    # rank1 is first place, rank2 is second-place, rank3 third-place.
    # rank83 is 83rd place, the lowest-ranked for nmses < 1.0 (in round 7)
    cex_vals = _cex_vals()
    rank1_vals = _rank1_vals()
    rank2_vals = _rank2_vals()
    rank3_vals = _rank3_vals()
    rank83_vals = _rank83_vals()

    do_plot = False  # only set to True for local testing

    rank1_nmse_meas = calc_nmse(cex_vals, rank1_vals)
    if do_plot:
        plot_prices(cex_vals, rank1_vals, f"Rank1. nmse={rank1_nmse_meas:.3e}")
    rank1_nmse_target = 1.569e-01
    assert rank1_nmse_meas == approx(rank1_nmse_target, rel=0.50, abs=0.1e-6)

    rank2_nmse_meas = calc_nmse(cex_vals, rank2_vals)
    if do_plot:
        plot_prices(cex_vals, rank1_vals, f"Rank2. nmse={rank2_nmse_meas:.3e}")
    rank2_nmse_target = 2.803e-01
    assert rank2_nmse_meas == approx(rank2_nmse_target, rel=0.50, abs=0.1e-6)

    rank3_nmse_meas = calc_nmse(cex_vals, rank3_vals)
    if do_plot:
        plot_prices(cex_vals, rank2_vals, f"Rank3. nmse={rank3_nmse_meas:.3e}")
    rank3_nmse_target = 3.349e-01
    assert rank3_nmse_meas == approx(rank3_nmse_target, rel=0.50, abs=0.1e-6)
    rank83_nmse_meas = calc_nmse(cex_vals, rank83_vals)
    if do_plot:
        plot_prices(cex_vals, rank83_vals, f"Rank83. nmse={rank83_nmse_meas:.3e}")
    rank83_nmse_target = 9.323e02
    assert rank83_nmse_meas == approx(rank83_nmse_target, rel=0.50, abs=0.1e-6)

    assert (
        0.0
        < rank1_nmse_target
        < rank2_nmse_target
        < rank3_nmse_target
        < rank83_nmse_target
    )
    assert rank3_nmse_target < 1.0  # rank83 nmse could be >1.0

    assert 0.0 < rank1_nmse_meas < rank2_nmse_meas < rank3_nmse_meas < rank83_nmse_meas
    assert rank3_nmse_meas < 1.0  # rank83 nmse could be >1.0


@enforce_types
def _cex_vals():
    return [
        1910.55,
        1908.81,
        1910.34,
        1912.62,
        1912.3,
        1906.73,
        1907.19,
        1906.07,
        1903.51,
        1905.29,
        1904.49,
        1904.94,
    ]


def _rank1_vals():
    # rank1 is NFT #232/252. From 0xa98e504040b68e6a281fd489fcd1658df9703a91
    # - old nmse measure = 1.154e-06
    return [
        1909.8423071678906,
        1909.3890122067048,
        1909.0222544696958,
        1908.606595942218,
        1908.221036039253,
        1907.8194953230318,
        1907.4288513924025,
        1907.0334268573008,
        1906.6423661565814,
        1906.250335445668,
        1905.8604458939187,
        1905.4708827925176,
    ]


def _rank2_vals():
    # rank2 is NFT #108/252. From 0xca27c95f0eea6a0645dd7dddac46dfa893099fd6
    # - old nmse measure = 2.062e-06
    return [
        1911.36499651,
        1911.45471804,
        1907.85007032,
        1907.76035838,
        1908.34218631,
        1908.09114526,
        1907.87335393,
        1907.54652541,
        1907.35899274,
        1907.67254935,
        1907.21127253,
        1907.06131286,
    ]


def _rank3_vals():
    # rank3 is NFT #237/252. From 0x9cb9a72299f715cbd58bcdf8b7fdc1107631114e
    # - old nmse measure = 2.463e-06
    return [
        1910.3733053054548,
        1910.082665202505,
        1910.0324737706073,
        1909.7306240431174,
        1909.687171551225,
        1909.38118747041,
        1909.337257891959,
        1909.0343962949887,
        1908.9827923561074,
        1908.6900915386434,
        1908.624031004779,
        1908.3479237283066,
    ]


def _rank83_vals():
    # rank83 is NFT #106/252. From 0xd9b371ad6d6ee59315b7c1bb891fc4e85fbeaae5
    # - old nmse measure = 6.856e-03
    return [
        2065.89,
        2065.62,
        2065.62,
        2065.62,
        2063.42,
        2068.25,
        2065.89,
        2068.36,
        2065.89,
        2065.89,
        2063.82,
        2063.72,
    ]
