from datetime import datetime
from enforce_typing import enforce_types

@enforce_types
def timestrToBlock(chain, timestr:str) -> int:
    """
    Examples: 2022-03-29 17:55 --> 4928
              2022-03-29 --> 4928 (earliest block of the day)

    @arguments
      chain -- brownie.networks.chain
      timestr -- str - YYYY-MM-DD | YYYY-MM-DD HH:MM
    @return
      block -- int
    """
    timestamp = timestrToTimestamp(timestr)
    block = timestampToBlock(chain, timestamp)
    return block

@enforce_types
def timestrToTimestamp(timestr:str) -> float:
    """Examples: 2022-03-29 17:55 --> 1648872899.3 (unix time)
                 2022-03-29 --> 1648872899.0
    """
    ncolon = timestr.count(":")
    if ncolon == 1:
        d = datetime.strptime(timestr, "%Y-%m-%d %H:%M")
    else:
        d = datetime.strptime(timestr, "%Y-%m-%d")
    return d.timestamp()

@enforce_types
def timestampToBlock(chain, timestamp:float) -> int:
    """Example: 1648872899.0 --> 4928"""
    raise NotImplementedError('build me')

    #1. get block 0 timestamp, block N timestamp, then bisect-search
    #2. https://github.com/ethereum/web3.py/issues/1872#issuecomment-932675448
    #3. https://github.com/ethereum/web3.py/issues/1872#issuecomment-1041224541
