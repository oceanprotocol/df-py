from datetime import datetime, timezone, date, timedelta
from math import ceil
from typing import Union

from enforce_typing import enforce_types
from scipy import optimize


@enforce_types
def getBlockNumberThursday(chain) -> int:
    timestamp = getNextThursdayTimestamp()
    block_number = timestampToFutureBlock(chain, timestamp)

    ## round to upper 100th
    block_number = ceil(block_number / 100) * 100
    return block_number


@enforce_types
def getNextThursdayTimestamp() -> int:
    d = date.today()
    if d.strftime("%a") == "Thu":
        d += timedelta(1)  # add a day so it doesn't return today

    while d.strftime("%a") != "Thu":
        d += timedelta(1)
    return int(d.strftime("%s"))


@enforce_types
def timestrToBlock(chain, timestr: str, test_eth: bool = False) -> int:
    """
    Examples: 2022-03-29_17:55 --> 4928
              2022-03-29 --> 4928 (earliest block of the day)

    @arguments
      chain -- brownie.networks.chain
      timestr -- str - YYYY-MM-DD | YYYY-MM-DD_HH:MM | YYYY-MM-DD_HH:MM:SS
    @return
      block -- int
    """
    timestamp = timestrToTimestamp(timestr)
    if chain.id == 1 or test_eth:
        # more accurate for mainnet
        block = ethTimestamptoBlock(chain, timestamp)
        block = ethFindClosestBlock(chain, block, timestamp)
        return block

    return timestampToBlock(chain, timestamp)


@enforce_types
def timestrToTimestamp(timestr: str) -> float:
    """Examples: 2022-03-29_17:55 --> 1648872899.3 (unix time)
    2022-03-29 --> 1648872899.0
    Does not use local time, rather always uses UTC
    """
    ncolon = timestr.count(":")
    if ncolon == 1:
        dt = datetime.strptime(timestr, "%Y-%m-%d_%H:%M")
    elif ncolon == 2:
        dt = datetime.strptime(timestr, "%Y-%m-%d_%H:%M:%S")
    else:
        dt = datetime.strptime(timestr, "%Y-%m-%d")

    # obtain POSIX timestamp. https://docs.python.org/3/library/datetime.html
    timestamp = dt.replace(tzinfo=timezone.utc).timestamp()

    return timestamp


@enforce_types
def timestampToFutureBlock(chain, timestamp: Union[float, int]) -> int:
    def timeSinceTimestamp(block_i):
        return chain[int(block_i)].timestamp

    block_last_number = len(chain) - 1

    # 40,000 is the average number of blocks per week
    block_old_number = max(0, block_last_number - 40_000)  # go back 40,000 blocks

    block_last_time = timeSinceTimestamp(block_last_number)  # time of last block
    block_old_time = timeSinceTimestamp(block_old_number)  # time of old block

    assert block_last_time < timestamp

    # slope
    m = (block_last_number - block_old_number) / (block_last_time - block_old_time)

    # y-intercept
    b = block_last_number - block_last_time * m

    # y = mx + b
    # y block number
    # x block time

    # thus
    estimated_block_number = m * timestamp + b
    return int(estimated_block_number)


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


@enforce_types
def ethTimestamptoBlock(chain, timestamp: Union[float, int]) -> int:
    """Example: 1648872899.0 --> 4928"""
    current_block = chain[-1].number
    current_time = chain[-1].timestamp
    return ethCalcBlockNumber(
        int(current_time), int(current_block), int(timestamp), chain
    )


@enforce_types
def ethCalcBlockNumber(ts: int, block: int, target_ts: int, chain):
    AVG_BLOCK_TIME = 12.06  # seconds
    diff = target_ts - ts
    diff_blocks = int(diff // AVG_BLOCK_TIME)
    block += diff_blocks
    ts_found = chain[block].timestamp
    if abs(ts_found - target_ts) > 12 * 5:
        return ethCalcBlockNumber(ts_found, block, target_ts, chain)

    return block


@enforce_types
def ethFindClosestBlock(chain, block_number: int, timestamp: Union[float, int]) -> int:
    """
    @arguments
        chain -- brownie.networks.chain
        block_number -- int
        timestamp -- int
    @return
        block_number -- int
    @description
        Finds the closest block number to given timestamp
    """

    block_ts = chain[block_number].timestamp
    found = block_number

    last = None
    if block_ts > timestamp:
        # search backwards
        while True:
            last = found
            found -= 1
            if chain[found].timestamp < timestamp:
                break

    else:
        # search forwards
        while True:
            last = found
            found += 1
            if chain[found].timestamp > timestamp:
                break
    if abs(chain[last].timestamp - timestamp) < abs(chain[found].timestamp - timestamp):
        found = last
    return found


@enforce_types
def getstfinBlocks(chain, ST, FIN):
    if "-" in ST:
        st_block = timestrToBlock(chain, ST)
    else:
        st_block = int(ST)

    if FIN == "latest":
        fin_block = len(chain) - 5
    elif FIN == "thu":
        fin_block = getBlockNumberThursday(chain)
    elif "-" in FIN:
        fin_block = timestrToBlock(chain, FIN)
    else:
        fin_block = int(FIN)

    return (st_block, fin_block)
