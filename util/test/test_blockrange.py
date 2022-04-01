import pytest

from util.blockrange import BlockRange

def test_StartEndClash():
    with pytest.raises(Exception):
        BlockRange(start_block=20, end_block=10, num_samples=5)

def test_availableN_samples0():
    r = BlockRange(start_block=10, end_block=20, num_samples=0).getRange()
    assert r == []
    
def test_available1_samples1():
    r = BlockRange(start_block=10, end_block=10, num_samples=1).getRange()
    assert r == [10]

def test_available1_samplesN():
    r = BlockRange(start_block=10, end_block=10, num_samples=10).getRange()
    assert r == [10]

def test_available2_samples1():
    for i in range(10):
        r = BlockRange(start_block=10, end_block=11, num_samples=1).getRange()
        assert r == [10] or r == [11]
    
def test_available2_samplesN():
    r = BlockRange(start_block=10, end_block=11, num_samples=10).getRange()
    assert sorted(r) == [10,11]

def test_available3_samples1():
    r = BlockRange(start_block=10, end_block=12, num_samples=1).getRange()
    assert r == [10] or r == [11] or r == [12]

def test_available3_samplesN():
    for i in range(10):
        r = BlockRange(start_block=10, end_block=12, num_samples=10).getRange()
        assert r == [10, 11, 12] # should always be sorted
            
def test_manyRandom():
    for i in range(100):
        r = BlockRange(start_block=10, end_block=20, num_samples=3).getRange()
        assert len(r) == 3
        assert min(r) >= 10
        assert max(r) <= 20
        assert r == sorted(r)

def test_general():
    br = BlockRange(start_block=10, end_block=20, num_samples=3)
    assert len(br.getRange()) == 3
    assert br.numBlocks() == 3
    assert "BlockRange" in str(br)
    
