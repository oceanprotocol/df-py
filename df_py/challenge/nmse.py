import numpy as np
from enforce_typing import enforce_types

@enforce_types
def calc_nmse(y: list, yhat: list) -> float:
    assert len(y) == len(yhat)

    y, yhat = np.asarray(y), np.asarray(yhat)

    ymin, ymax = min(y), max(y)
    yrange = ymax - ymin

    # First, scale true values and predicted values such that:
    # - true values are in range [0.0, 1.0]
    # - predicted values follow the same scaling factors
    y01 = (y - ymin) / yrange
    yhat01 = (yhat - ymin) / yrange
    
    mse_xy = np.sum(np.square(y01 - yhat01))
    mse_x = np.sum(np.square(y01))
    nmse = mse_xy / mse_x

    return nmse


@enforce_types
def plot_prices(cex_vals: list, pred_vals: list, extra_title=""):
    # this is used for local testing only. Therefore import last-minute
    # pre-requisite, from console:
    #  pip3 install matplotlib
    #  sudo apt-get install python3-tk
    import matplotlib
    import matplotlib.pyplot as plt

    matplotlib.rcParams.update({"font.size": 10})
    x = [h for h in range(0, 12)]
    assert len(x) == len(cex_vals) == len(pred_vals)
    fig, ax = plt.subplots()
    ax.plot(x, cex_vals, "--o", label="CEX values")
    ax.plot(x, pred_vals, "-o", label="Pred. values")
    ax.legend(loc="lower right")
    plt.ylabel("ETH price")
    plt.xlabel("Hour")
    plt.title(f"Pred. vs actual/CEX. {extra_title}")
    fig.set_size_inches(9, 6)
    plt.xticks(x)
    plt.show()
