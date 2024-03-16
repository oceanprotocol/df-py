import pytest
from enforce_typing import enforce_types

from df_py.blockutil.blockrange import BlockRange


@enforce_types
def test_failures():
    with pytest.raises(Exception):  # end < start
        BlockRange(st=20, fin=10, num_samples=5)

    with pytest.raises(Exception):  # arg1 negative
        BlockRange(st=-1, fin=10, num_samples=5)

    with pytest.raises(Exception):  # arg2 negative
        BlockRange(st=1, fin=-1, num_samples=5)

    with pytest.raises(Exception):  # arg3 negative
        BlockRange(st=1, fin=10, num_samples=-5)


@enforce_types
def test_start_at_zero():
    r = BlockRange(st=0, fin=3, num_samples=10).get_blocks()
    assert r == [0, 1, 2, 3]


@enforce_types
def test_available_samples_0():
    r = BlockRange(st=10, fin=20, num_samples=0).get_blocks()
    assert r == []


@enforce_types
def test_available_samples_1():
    r = BlockRange(st=10, fin=10, num_samples=1).get_blocks()
    assert r == [10]


@enforce_types
def test_available_samples_N():
    r = BlockRange(st=10, fin=10, num_samples=10).get_blocks()
    assert r == [10]


@enforce_types
def test_available_samples_N2():
    for _ in range(10):
        r = BlockRange(st=10, fin=11, num_samples=1).get_blocks()
        assert r in ([10], [11])


@enforce_types
def test_available_samples_N3():
    r = BlockRange(st=10, fin=11, num_samples=10).get_blocks()
    assert sorted(r) == [10, 11]


@enforce_types
def test_available3_samplesN4():
    r = BlockRange(st=10, fin=12, num_samples=1).get_blocks()
    assert r in ([10], [11], [12])


@enforce_types
def test_available3_samplesN5():
    for _ in range(10):
        r = BlockRange(st=10, fin=12, num_samples=10).get_blocks()
        assert r == [10, 11, 12]  # should always be sorted


@enforce_types
def test_many_random():
    for _ in range(100):
        r = BlockRange(st=10, fin=20, num_samples=3).get_blocks()
        assert len(r) == 3
        assert min(r) >= 10
        assert max(r) <= 20
        assert r == sorted(r)


@enforce_types
def test_general():
    br = BlockRange(st=10, fin=20, num_samples=3)
    assert len(br.get_blocks()) == 3
    assert br.num_blocks() == 3
    assert "BlockRange" in str(br)


@enforce_types
def test_filter_by_max():
    br = BlockRange(st=10, fin=5000, num_samples=100)
    before = br.get_blocks()

    br.filter_by_max_block(max_block=2500)
    after = br.get_blocks()

    assert len(before) != len(after)  # should be different

    assert max(after) <= 2500  # max block should be <= 2500

    # pylint: disable=consider-using-enumerate
    for i in range(len(after)):
        assert after[i] in before  # should be in before


@enforce_types
def test_rnd_seed():
    r1 = BlockRange(st=10, fin=5000, num_samples=100, random_seed=42)
    r2 = BlockRange(st=10, fin=5000, num_samples=100, random_seed=43)
    assert r1.get_blocks() != r2.get_blocks()  # should be different

    s1 = BlockRange(st=10, fin=5000, num_samples=100, random_seed=42)
    s2 = BlockRange(st=10, fin=5000, num_samples=100, random_seed=42)
    assert s1.get_blocks() == s2.get_blocks()  # should be same


@enforce_types
def test_no_sampling():
    # should return fin if num_samples is 1
    rng = BlockRange(st=10, fin=20, num_samples=1)
    assert rng.get_blocks() == [20]
