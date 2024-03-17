from enforce_typing import enforce_types
import numpy as np
import pytest

from df_py.volume.rank import rank_based_allocate


@enforce_types
def test_rank_based_allocate_1_end_to_end():
    """
    @description
      Test the wrapper of RewardCalculator._rank_based_allocate()
      --> util_rank.rank_based_allocate()

      Whereas all the other tests are direct, on util_rank.rank_based_allocate()
    """
    V_USD = np.array([32.0], dtype=float)
    mock_calculator = MockRewardCalculator()
    mock_calculator.set_V_USD(V_USD)
    p = mock_calculator._rank_based_allocate()
    target_p = np.array([1.0], dtype=float)
    np.testing.assert_allclose(p, target_p)


@enforce_types
def test_rank_based_allocate_zerovols():
    V_USD = np.array([32.0, 0.0, 15.0], dtype=float)
    with pytest.raises(ValueError):
        _ = rank_based_allocate(V_USD)


@enforce_types
def test_rank_based_allocate_0():
    V_USD = np.array([], dtype=float)
    p = rank_based_allocate(V_USED)
    target_p = np.array([], dtype=float)
    np.testing.assert_allclose(p, target_p)


@enforce_types
def test_rank_based_allocate_1():
    V_USD = np.array([32.0], dtype=float)
    p = rank_based_allocate(V_USD)
    target_p = np.array([1.0], dtype=float)
    np.testing.assert_allclose(p, target_p)


@enforce_types
def test_rank_based_allocate_3_simple():
    V_USD = np.array([10.0, 99.0, 3.0], dtype=float)
    p = rank_based_allocate(V_USD, rank_scale_op="LIN")
    target_p = np.array([2.0 / 6.0, 3.0 / 6.0, 1.0 / 6.0], dtype=float)
    np.testing.assert_allclose(p, target_p)


@enforce_types
@pytest.mark.parametrize("op", ["LIN", "POW2", "POW4", "LOG", "SQRT"])
def test_rank_based_allocate_3_exact(op):
    V_USD = np.array([10.0, 99.0, 3.0], dtype=float)

    (p, ranks, max_N, allocs, I) = rank_based_allocate(
        V_USD, max_n_rank_assets=100, rank_scale_op=op, return_info=True
    )

    target_max_N = 3
    target_ranks = [2, 1, 3]
    target_I = [0, 1, 2]

    assert max_N == target_max_N
    assert min(allocs) > 0, f"had an alloc=0; op={op}, allocs={allocs}"
    assert min(p) > 0, f"had a p=0; op={op}, allocs={allocs}, p={p}"
    np.testing.assert_allclose(ranks, np.array(target_ranks, dtype=float))
    np.testing.assert_allclose(I, np.array(target_I, dtype=float))

    if op == "LIN":
        target_allocs = [2.0, 3.0, 1.0]
        target_p = np.array([2.0 / 6.0, 3.0 / 6.0, 1.0 / 6.0], dtype=float)
    elif op == "LOG":
        target_allocs = [0.352183, 0.653213, 0.176091]
        target_p = [0.298084, 0.552874, 0.149042]
    else:
        return

    target_allocs = np.array(target_allocs, dtype=float)
    target_p = np.array(target_p, dtype=float)

    np.testing.assert_allclose(allocs, target_allocs, rtol=1e-3)
    np.testing.assert_allclose(p, target_p, rtol=1e-3)


@enforce_types
def test_rank_based_allocate_20():
    V_USD = 1000.0 * np.random.rand(20)
    p = rank_based_allocate(V_USD)
    assert len(p) == 20
    assert sum(p) == pytest.approx(1.0)


@enforce_types
def test_rank_based_allocate_1000():
    V_USD = 1000.0 * np.random.rand(1000)
    p = rank_based_allocate(V_USD)
    assert len(p) == 1000
    assert sum(p) == pytest.approx(1.0)


@enforce_types
@pytest.mark.skip(reason="only unskip this when doing manual tuning")
def test_plot_ranks():
    # This function is for manual exploration around shapes of the rank curve
    # To use it:
    # 1. in this file, right above: comment out "pytest.mark.skip" line
    # 2. in console: pip install matplotlib
    # 3. in this file, right below: change any "settable values"
    # 4. in console: pytest util/test/test_calc_rewards.py::test_plot_ranks

    # settable values
    save_or_show = "save"  # "save" or "show"
    max_ns = [20, 50, 100]  # example list: [20, 50, 100]
    ops = [
        "LIN",
        "POW2",
        "POW4",
        "LOG",
        "SQRT",
    ]  # full list: ["LIN", "POW2", "POW4", "LOG", "SQRT"]

    # go!
    for max_n in max_ns:
        for op in ops:
            _plot_ranks(save_or_show, max_n, op)


@enforce_types
def _plot_ranks(save_or_show, max_n_rank_assets, rank_scale_op):
    # pylint: disable=unused-variable, import-outside-toplevel

    import matplotlib
    import matplotlib.pyplot as plt

    N = 120
    V_USD = np.arange(N, 0, -1)  # N, N-1, ..., 2, 1. Makes ranking obvious!

    p = rank_based_allocate(
        V_USD, max_n_rank_assets=max_n_rank_assets, rank_scale_op=rank_scale_op
    )

    if save_or_show == "save":
        fontsize = 6
        linewidth_m = 0.2
    elif save_or_show == "show":
        fontsize = 25
        linewidth_m = 1.0
    else:
        raise ValueError(save_or_show)

    matplotlib.rcParams.update({"font.size": fontsize})

    _, ax1 = plt.subplots()
    ax2 = ax1.twinx()

    x = np.arange(1, N + 1)
    ax1.bar(x, 100.0 * p)
    ax1.set_xlabel("DCV Rank of data asset (1=highest)")
    ax1.set_ylabel("% of OCEAN to data asset", color="b")

    ax2.plot(x, np.cumsum(100.0 * p), "g-", linewidth=3.5 * linewidth_m)
    ax2.set_ylabel("Cumulative % of OCEAN to assets", color="g")

    plt.title(
        "% of OCEAN to data asset vs rank"
        f". max_n_rank_assets={max_n_rank_assets}"
        f", rank_scale_op={rank_scale_op}"
    )

    # Show the major grid and style it slightly.
    ax1.grid(
        axis="y",
        which="major",
        color="#DDDDDD",
        linewidth=2.5 * linewidth_m,
        linestyle="-",
    )

    xticks = [1] + list(np.arange(10, N + 1, 5))
    xlabels = [str(xtick) for xtick in xticks]
    plt.xticks(xticks, xlabels)

    if save_or_show == "save":
        fname = f"max-{max_n_rank_assets:03d}_scale-{rank_scale_op}.png"
        plt.savefig(fname, dpi=300)
        print(f"Saved {fname}")
    elif save_or_show == "show":
        mng = plt.get_current_fig_manager()
        mng.resize(*mng.window.maxsize())
        plt.show()
    else:
        raise ValueError(save_or_show)
