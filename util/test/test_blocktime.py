from util.blocktime import timestrToBlock, timestrToTimestamp, \
    timestampToBlock

def test_timestrToBlock():
    pass

def test_timestrToTimestamp():
    assert timestrToTimestamp("1970-01-01 1:00") == 0.0
    assert timestrToTimestamp("2022-03-29 17:55") == 1648569300.0
    assert timestrToTimestamp("2022-03-29") == 1648504800.0

def test_timestampToBlock():
    pass

