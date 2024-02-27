from datetime import datetime, timedelta, timezone
from math import ceil
from typing import Union
from df_py.util.datanft_blocktime import get_block_number_from_datanft
from df_py.volume.reward_calculator import get_df_week_number

from enforce_typing import enforce_types
from scipy import optimize
from web3.main import Web3


@enforce_types
def get_block_number_thursday(web3) -> int:
    timestamp = get_next_thursday_timestamp(web3)
    block_number = timestamp_to_future_block(web3, timestamp)

    # round to upper 100th
    block_number = ceil(block_number / 100) * 100
    return block_number


@enforce_types
def get_next_thursday_timestamp(web3) -> int:
    chain_timestamp = web3.eth.get_block("latest").timestamp
    chain_time = datetime.fromtimestamp(chain_timestamp)

    chain_time = chain_time.replace(
        hour=0, minute=0, second=0, microsecond=0, tzinfo=timezone.utc
    )

    if chain_time.strftime("%a") == "Thu":
        chain_time += timedelta(days=1)  # add a day so it doesn't return today

    while chain_time.strftime("%a") != "Thu":
        chain_time += timedelta(days=1)

    return int(chain_time.timestamp())


@enforce_types
def timestr_to_block(web3, timestr: str, test_eth: bool = False) -> int:
    """
    Examples: 2022-03-29_17:55 --> 4928
              2022-03-29 --> 4928 (earliest block of the day)

    @arguments
      web3 -- web3 instance
      timestr -- str - YYYY-MM-DD | YYYY-MM-DD_HH:MM | YYYY-MM-DD_HH:MM:SS
    @return
      block -- int
    """
    timestamp = timestr_to_timestamp(timestr)
    if web3.eth.chain_id == 1 or test_eth:
        # more accurate for mainnet
        block = eth_timestamp_to_block(web3, timestamp)
        block = eth_find_closest_block(web3, block, timestamp)
        return block

    return timestamp_to_block(web3, timestamp)


@enforce_types
def timestr_to_timestamp(timestr: str) -> float:
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
def timestamp_to_future_block(web3, timestamp: Union[float, int]) -> int:
    def time_since_timestamp(block_i):
        return web3.eth.get_block(int(block_i)).timestamp

    block_last_number = web3.eth.get_block("latest").number

    # 40,000 is the average number of blocks per week
    block_old_number = max(0, block_last_number - 40_000)  # go back 40,000 blocks

    block_last_time = time_since_timestamp(block_last_number)  # time of last block
    block_old_time = time_since_timestamp(block_old_number)  # time of old block

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


class BlockTimestampComparer:
    def __init__(self, target_timestamp, web3):
        self.target_timestamp = target_timestamp
        self.web3 = web3

    def time_since_timestamp(self, block_i):
        try:
            block_timestamp = self.web3.eth.get_block(int(block_i)).timestamp
        except Exception as e:
            print(f"An exception occurred while getting block {block_i}, {e}")
            block_timestamp = 0
        return block_timestamp - self.target_timestamp


@enforce_types
def timestamp_to_block(web3, timestamp: Union[float, int]) -> int:
    """Example: 1648872899.0 --> 4928"""

    f = BlockTimestampComparer(timestamp, web3).time_since_timestamp
    a = 0
    b = web3.eth.get_block("latest").number

    if f(a) > 0 and f(b) > 0:  # corner case: everything's in the past
        if web3.eth.chain_id == 8996:
            return 0  # this situation is feasible on testnet

        # on other networks, the target will never be 0
        raise ValueError("timestamp_to_block() everything is in the past")

    if f(a) < 0 and f(b) < 0:  # corner case: everything's in the future
        return web3.eth.get_block("latest").number

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
    block_found = web3.eth.get_block(int(block_i))
    block_timestamp = block_found.timestamp

    if abs(block_timestamp - timestamp) > 60 * 15:
        # pylint: disable=line-too-long
        print(
            "WARNING: timestamp_to_block() is returning a block that is more than 15 minutes away from the target timestamp"
        )
        print("target timestamp =", timestamp)
        print("block timestamp =", block_timestamp)
        print("block number =", block_i)
        print("delta =", abs(block_timestamp - timestamp))
        raise ValueError(
            "timestamp_to_block() is returning a block that is too far away"
        )
    print(
        "Returning block number",
        block_i,
        "for timestamp",
        timestamp,
        "diff",
        abs(block_timestamp - timestamp),
    )
    return int(block_i)


@enforce_types
def eth_timestamp_to_block(web3, timestamp: Union[float, int]) -> int:
    """Example: 1648872899.0 --> 4928"""
    block = web3.eth.get_block("latest")
    current_block = block.number
    current_time = block.timestamp
    return eth_calc_block_number(
        int(current_time), int(current_block), int(timestamp), web3
    )


@enforce_types
def eth_calc_block_number(ts: int, block: int, target_ts: int, web3):
    AVG_BLOCK_TIME = 12.06  # seconds
    diff = target_ts - ts
    diff_blocks = int(diff // AVG_BLOCK_TIME)
    block += diff_blocks
    ts_found = web3.eth.get_block(block).timestamp
    if abs(ts_found - target_ts) > 12 * 5:
        return eth_calc_block_number(ts_found, block, target_ts, web3)

    return block


@enforce_types
def eth_find_closest_block(
    web3: Web3, block_number: int, timestamp: Union[float, int]
) -> int:
    """
    @arguments
        web3 -- Web3 instance
        block_number -- int
        timestamp -- int
    @return
        block_number -- int
    @description
        Finds the closest block number to given timestamp
    """

    block_ts = web3.eth.get_block(block_number).timestamp  # type: ignore[attr-defined]
    found = block_number

    last = None
    if block_ts > timestamp:
        # search backwards
        while True:
            last = found
            found -= 1
            if web3.eth.get_block(found).timestamp < timestamp:  # type: ignore[attr-defined]
                break

    else:
        # search forwards
        while True:
            last = found
            found += 1
            if web3.eth.get_block(found).timestamp > timestamp:  # type: ignore[attr-defined]
                break

    if abs(web3.eth.get_block(last).timestamp - timestamp) < abs(  # type: ignore[attr-defined]
        web3.eth.get_block(found).timestamp - timestamp  # type: ignore[attr-defined]
    ):
        found = last

    return found


@enforce_types
def get_fin_block(web3, FIN):
    fin_block = 0
    if FIN == "latest":
        fin_block = web3.eth.get_block("latest").number - 4
    elif FIN == "thu":
        fin_block = get_block_number_thursday(web3)
    elif "-" in str(FIN):
        fin_block = timestr_to_block(web3, FIN)
    else:
        fin_block = int(FIN)
    return fin_block


@enforce_types
def get_st_block(web3, ST, use_data_nft: bool = False):
    st_block = 0

    if use_data_nft:
        timestamp = timestr_to_timestamp(ST) if "-" in str(ST) else int(ST)
        date = datetime.fromtimestamp(timestamp)
        df_week = get_df_week_number(date)
        chainid = web3.eth.chain_id
        block_number = get_block_number_from_datanft(chainid, df_week)
        block_found = web3.eth.get_block(block_number)
        block_timestamp = block_found.timestamp
        if abs(block_timestamp - timestamp) > 60 * 15:
            print("The recorded block number is too far from the target")
            print("Canceling use_data_nft")
        else:
            return block_number
    if "-" in str(ST):
        st_block = timestr_to_block(web3, ST)
    else:
        st_block = int(ST)
    return st_block


@enforce_types
def get_st_fin_blocks(web3, ST, FIN):
    st_block = get_st_block(web3, ST)
    fin_block = get_fin_block(web3, FIN)
    return (st_block, fin_block)
