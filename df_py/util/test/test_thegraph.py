from pprint import pprint
from unittest.mock import Mock, patch

import pytest
from enforce_typing import enforce_types
from requests import Response

from df_py.util import networkutil, oceantestutil
from df_py.util.graphutil import submit_query

CHAINID = networkutil.DEV_CHAINID


@enforce_types
def test_approved_tokens():
    query = "{ opcs{approvedTokens} }"
    result = submit_query(query, CHAINID)

    pprint(result)


@enforce_types
def test_connection_failure():
    query = "{ opcs{approvedTokens} }"
    with pytest.raises(Exception, match="Query failed"):
        with patch("df_py.util.graphutil.requests.post") as mock:
            response = Mock(spec=Response)
            response.status_code = 500
            mock.return_value = response
            submit_query(query, CHAINID)


@enforce_types
def setup_function():
    oceantestutil.fill_accounts_with_OCEAN(oceantestutil.get_all_accounts())
