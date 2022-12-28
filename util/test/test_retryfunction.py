from enforce_typing import enforce_types
from util.retry import retryFunction
from pytest import raises

testfunc_callcount = 0


@enforce_types
def test_retryFunction():
    # pylint: disable=global-variable-undefined
    global testfunc_callcount
    testfunc_callcount = 0

    def testfunc_fail(some_arg: int):
        # pylint: disable=global-variable-undefined
        global testfunc_callcount
        testfunc_callcount += 1
        if testfunc_callcount == 3:
            return testfunc_callcount + some_arg
        raise Exception("failed")

    some_arg = 1
    assert (
        retryFunction(testfunc_fail, 3, 0.1, some_arg) == testfunc_callcount + some_arg
    )
    testfunc_callcount = 0

    with raises(Exception):
        retryFunction(testfunc_fail, 2, 0.1, some_arg)
    testfunc_callcount = 0

    with raises(Exception):
        retryFunction(testfunc_fail, 1, 0.1, some_arg)
    testfunc_callcount = 0
