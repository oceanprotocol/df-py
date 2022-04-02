
def datetimeToBlock(chain, datetime):
    """
    @arguments
      chain -- brownie.networks.chain
      datetime -- YYYY:MM:DD | YYYY:MM:DD:HH:MM
    @return
      block -- int
    """
    
    timestamp = datetimeToTimestamp(datetime) #timestamp = unix time
    block = timestampToBlock(chain, timestamp)
    return block

def datetimeToTimestamp(datetime):
    raise NotImplementedError('build me')
    #see https://note.nkmk.me/en/python-unix-time-datetime/

def timestampToBlock(chain, timestamp):    
    raise NotImplementedError('build me')

    #1. get block 0 timestamp, block N timestamp, then bisect-search
    #2. https://github.com/ethereum/web3.py/issues/1872#issuecomment-932675448
    #3. https://github.com/ethereum/web3.py/issues/1872#issuecomment-1041224541
