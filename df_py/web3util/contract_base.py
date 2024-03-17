#
# Copyright 2023 Ocean Protocol Foundation
# SPDX-License-Identifier: Apache-2.0
#

"""All contracts inherit from `ContractBase` class."""
import logging
from typing import Optional

from enforce_typing import enforce_types
from web3.main import Web3  # pylint: disable=no-name-in-module

from df_py.web3util.contract_utils import deploy_contract, load_contract

logger = logging.getLogger(__name__)


def function_wrapper(contract, web3, contract_functions, func_name):
    # direct function calls
    if hasattr(contract, func_name):
        return getattr(contract, func_name)

    # contract functions
    def wrap(*args, **kwargs):
        args2 = list(args)

        tx_dict = None

        # retrieve tx dict from either args or kwargs
        if args and isinstance(args[-1], dict):
            tx_dict = args[-1] if args[-1].get("from") else None
            args2 = list(args[:-1])

        if "tx_dict" in kwargs:
            tx_dict = kwargs["tx_dict"] if kwargs["tx_dict"].get("from") else None
            del kwargs["tx_dict"]

        # use addresses instead of wallets when doing the call
        for arg in args2:
            if hasattr(arg, "address"):
                args2 = list(args2)
                args2[args2.index(arg)] = arg.address

        func = getattr(contract_functions, func_name)
        result = func(*args2, **kwargs)

        # view/pure functions don't need "from" key in tx_dict
        if not tx_dict and result.abi["stateMutability"] not in ["view", "pure"]:
            raise Exception("Needs tx_dict with 'from' key.")

        if tx_dict and "from" in tx_dict:
            # if it's a transaction, build and send it
            wallet = tx_dict["from"]
            tx_dict2 = tx_dict.copy()
            tx_dict2["nonce"] = web3.eth.get_transaction_count(wallet.address)
            tx_dict2["from"] = tx_dict["from"].address
        else:
            tx_dict2 = tx_dict or {}

        # if it's a view/pure function, just call it
        if result.abi["stateMutability"] in ["view", "pure"]:
            return result.call(tx_dict2)

        result = result.build_transaction(tx_dict2)

        # sign with wallet private key and send transaction
        signed_tx = web3.eth.account.sign_transaction(result, wallet._private_key)
        receipt = web3.eth.send_raw_transaction(signed_tx.rawTransaction)

        return web3.eth.wait_for_transaction_receipt(receipt)

    return wrap


class ContractBase:
    """Base class for all contract objects."""

    @enforce_types
    def __init__(
        self,
        web3: Web3,
        path: str,
        address: Optional[str] = None,
        constructor_args: Optional[list] = None,
    ) -> None:
        """Initialises Contract Base object."""
        if constructor_args is not None:
            self.contract = deploy_contract(web3, path, constructor_args)
        elif address is not None:
            self.contract = load_contract(web3, path, web3.to_checksum_address(address))
        assert not address or (self.contract.address.lower() == address.lower())

        transferable = [
            x for x in dir(self.contract.functions) if not x.startswith("_")
        ]

        # transfer contract functions to ContractBase object
        for function in transferable:
            setattr(
                self,
                function,
                function_wrapper(
                    self.contract,
                    web3,
                    self.contract.functions,
                    function,
                ),
            )
