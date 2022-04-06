from util import getrate

def test1():
    nsamp = 5
    seed = 32
    rate = getrate.getrate(
        "OCEAN", "2022-01-20_00:00", "2022-01-26_23:59", nsamp, seed)
    assert 0.2 <= rate <= 2.00
        
