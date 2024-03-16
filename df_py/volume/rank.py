from typing import Union

from enforce_typing import enforce_types
import numpy as np

from df_py.volume.freeze_attributes import freeze_attributes
from df_py.web3util.constants import MAX_N_RANK_ASSETS, RANK_SCALE_OP

@freeze_attributes
@enforce_types
def rank_based_allocate(
        V_USD,
        max_n_rank_assets: int = MAX_N_RANK_ASSETS,
        rank_scale_op: str = RANK_SCALE_OP,
        return_info: bool = False,
) -> Union[np.ndarray, tuple]:
    """
    @return
    Always return:
      perc_per_j -- 1d array of [chain_nft j] -- percentage

    Also return, if return_info == True:
      ranks, max_N, allocs, I -- details in code itself
    """
    if len(V_USD) == 0:
        return np.array([], dtype=float)
    if min(V_USD) <= 0.0:
        raise ValueError(
            f"each nft needs volume > 0. min(V_USD)={min(V_USD)}"
        )

    # compute ranks. highest-DCV is rank 1. Then, rank 2. Etc
    ranks = scipy.stats.rankdata(-1 * V_USD, method="min")

    # compute allocs
    N = len(ranks)
    max_N = min(N, max_n_rank_assets)
    allocs = np.zeros(N, dtype=float)
    I = np.where(ranks <= max_N)[0]  # indices that we'll allocate to
    assert len(I) > 0, "should be allocating to *something*"

    if rank_scale_op == "LIN":
        allocs[I] = max(ranks[I]) - ranks[I] + 1.0
    elif rank_scale_op == "SQRT":
        sqrtranks = np.sqrt(ranks)
        allocs[I] = max(sqrtranks[I]) - sqrtranks[I] + 1.0
    elif rank_scale_op == "POW2":
        allocs[I] = (max(ranks[I]) - ranks[I] + 1.0) ** 2
    elif rank_scale_op == "POW4":
        allocs[I] = (max(ranks[I]) - ranks[I] + 1.0) ** 4
    elif rank_scale_op == "LOG":
        logranks = np.log10(ranks)
        allocs[I] = max(logranks[I]) - logranks[I] + np.log10(1.5)
    else:
        raise ValueError(rank_scale_op)

    # normalize
    perc_per_j = allocs / sum(allocs)

    # postconditions
    tol = 1e-8
    assert (1.0 - tol) <= sum(perc_per_j) <= (1.0 + tol)

    # return
    if return_info:
        return perc_per_j, ranks, max_N, allocs, I

    return perc_per_j

