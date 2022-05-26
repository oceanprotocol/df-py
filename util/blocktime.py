from datetime import datetime, timezone
from typing import Union

from enforce_typing import enforce_types
from scipy import optimize


@enforce_types
def timestrToBlock(chain, timestr: str) -> int:
    """
    Examples: 2022-03-29_17:55 --> 4928
              2022-03-29 --> 4928 (earliest block of the day)

    @arguments
      chain -- brownie.networks.chain
      timestr -- str - YYYY-MM-DD | YYYY-MM-DD_HH:MM
    @return
      block -- int
    """
    timestamp = timestrToTimestamp(timestr)
    block = timestampToBlock(chain, timestamp)
    return block


@enforce_types
def timestrToTimestamp(timestr: str) -> float:
    """Examples: 2022-03-29_17:55 --> 1648872899.3 (unix time)
    2022-03-29 --> 1648872899.0
    Does not use local time, rather always uses UTC
    """
    ncolon = timestr.count(":")
    if ncolon == 1:
        dt = datetime.strptime(timestr, "%Y-%m-%d_%H:%M")
    else:
        dt = datetime.strptime(timestr, "%Y-%m-%d")

    # obtain POSIX timestamp. https://docs.python.org/3/library/datetime.html
    timestamp = dt.replace(tzinfo=timezone.utc).timestamp()

    return timestamp


@enforce_types
def timestampToBlock(chain, timestamp: Union[float, int]) -> int:
    """Example: 1648872899.0 --> 4928"""

    class C:
        def __init__(self, target_timestamp):
            self.target_timestamp = target_timestamp

        def timeSinceTimestamp(self, block_i):
            block_timestamp = chain[int(block_i)].timestamp
            return block_timestamp - self.target_timestamp

    f = C(timestamp).timeSinceTimestamp
    a = 0
    b = len(chain) - 1

    if f(a) > 0 and f(b) > 0:  # corner case: everything's in the past
        return 0

    if f(a) < 0 and f(b) < 0:  # corner case: everything's in the future
        return len(chain)

    # pylint: disable=unused-variable
    (block_i, results) = optimize.bisect(f, a, b, xtol=0.4, full_output=True)

    # uncomment to debug
    # ---
    # print(f"iterations = {results.iterations}")
    # print(f"function calls = {results.function_calls}")
    # print(f"converged? {results.converged}")
    # print(f"cause of termination? {results.flag}")
    # print("")
    # print(f"target timestamp = {timestamp}")
    # print(f"distToTargetTimestamp(a=0) = {f(0)}")
    # print(f"distToTargetTimestamp(b={b}) = {f(b)}")
    # print(f"distToTargetTimestamp(result=block_i={block_i}) = {f(block_i)}")
    # ---

    return int(block_i)
