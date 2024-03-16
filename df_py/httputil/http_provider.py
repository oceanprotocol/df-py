#
# Copyright 2023 Ocean Protocol Foundation
# SPDX-License-Identifier: Apache-2.0
#
from web3 import HTTPProvider, WebsocketProvider

from df_py.httputil.request import make_post_request


class CustomHTTPProvider(HTTPProvider):
    """
    Override requests to control the connection pool to make it blocking.
    """

    def make_request(self, method, params):
        self.logger.debug(
            "Making request HTTP. URI: %s, Method: %s", self.endpoint_uri, method
        )
        request_data = self.encode_rpc_request(method, params)

        # pylint: disable=not-a-mapping
        raw_response = make_post_request(
            self.endpoint_uri, request_data, **self.get_request_kwargs()
        )
        response = self.decode_rpc_response(raw_response)
        self.logger.debug(
            "Getting response HTTP. URI: %s, Method: %s, Response: %s",
            self.endpoint_uri,
            method,
            response,
        )
        return response


def get_web3_connection_provider(network_url):
    if network_url.startswith("http"):
        return CustomHTTPProvider(network_url)

    if network_url.startswith("ws"):
        return WebsocketProvider(network_url)

    raise Exception(f"Unsupported network url: {network_url}")
