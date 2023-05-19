from enforce_typing import enforce_types

from util import graphutil, networkutil


@enforce_types
def test_approvedTokens():
    query = "{ opcs{approvedTokens} }"
    result = graphutil.submitQuery(query, networkutil.DEV_CHAINID)
    print(result)
