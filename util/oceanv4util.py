from collections import namedtuple
from enforce_typing import enforce_types
import json
from typing import Any, List, Dict, Tuple

import brownie

from util.base18 import toBase18
from util.constants import (
    BROWNIE_PROJECT,
    GOD_ACCOUNT,
    ZERO_ADDRESS,
    OPF_ADDRESS,
)
from util.globaltokens import OCEANtoken

_ERC721_TEMPLATE = None


@enforce_types
def ERC721Template():
    global _ERC721_TEMPLATE  # pylint: disable=global-statement
    try:
        erc721_template = _ERC721_TEMPLATE  # may trigger failure
        if erc721_template is not None:
            x = erc721_template.address  # "" # pylint: disable=unused-variable
    except brownie.exceptions.ContractNotFound:
        erc721_template = None
    if erc721_template is None:
        _ERC721_TEMPLATE = BROWNIE_PROJECT.ERC721Template.deploy(
            {"from": GOD_ACCOUNT}
        )
        erc721_template = _ERC721_TEMPLATE
    return erc721_template


_ERC20_TEMPLATE = None


@enforce_types
def ERC20Template():
    global _ERC20_TEMPLATE  # pylint: disable=global-statement
    try:
        erc20_template = _ERC20_TEMPLATE  # may trigger failure
        if erc20_template is not None:
            x = erc20_template.address  # "" # pylint: disable=unused-variable
    except brownie.exceptions.ContractNotFound:
        erc20_template = None
    if erc20_template is None:
        _ERC20_TEMPLATE = BROWNIE_PROJECT.ERC20Template.deploy({"from": GOD_ACCOUNT})
        erc20_template = _ERC20_TEMPLATE
    return erc20_template


_POOL_TEMPLATE = None


@enforce_types
def POOLTemplate():
    global _POOL_TEMPLATE  # pylint: disable=global-statement
    try:
        pool_template = _POOL_TEMPLATE  # may trigger failure
        if pool_template is not None:
            x = pool_template.address  # "" # pylint: disable=unused-variable
    except brownie.exceptions.ContractNotFound:
        pool_template = None
    if pool_template is None:
        _POOL_TEMPLATE = BROWNIE_PROJECT.BPool.deploy({"from": GOD_ACCOUNT})
        pool_template = _POOL_TEMPLATE

    return pool_template


@enforce_types
def deployRouter(from_account):
    OCEAN = OCEANtoken()
    pool_template = POOLTemplate()
    router = BROWNIE_PROJECT.FactoryRouter.deploy(
        from_account.address,
        OCEAN.address,
        pool_template,
        OPF_ADDRESS,
        [],
        {"from": from_account},
    )
    return router


@enforce_types
def deployERC721Factory(from_account, router):
    erc721_template = ERC721Template()
    erc20_template = ERC20Template()
    factory = BROWNIE_PROJECT.ERC721Factory.deploy(
        erc721_template.address,
        erc20_template.address,
        OPF_ADDRESS,
        router.address,
        {"from": from_account},
    )
    return factory


@enforce_types
def createDataNFT(name: str, symbol: str, from_account, router):
    erc721_factory = deployERC721Factory(from_account, router)
    erc721_template_index = 1
    token_URI = "https://mystorage.com/mytoken.png"
    tx = erc721_factory.deployERC721Contract(
        name,
        symbol,
        erc721_template_index,
        router.address,
        ZERO_ADDRESS,  # additionalMetaDataUpdater set to 0x00 for now
        token_URI,
        {"from": from_account},
    )
    data_NFT_address = tx.events["NFTCreated"]["newTokenAddress"]
    data_NFT = BROWNIE_PROJECT.ERC721Template.at(data_NFT_address)
    return (data_NFT, erc721_factory)


@enforce_types
def createDatatokenFromDataNFT(
    DT_name: str, DT_symbol: str, DT_cap: int, dataNFT, from_account
):

    erc20_template_index = 1
    strings = [
        DT_name,
        DT_symbol,
    ]
    addresses = [
        from_account.address,  # minter
        from_account.address,  # fee mgr
        from_account.address,  # pub mkt
        ZERO_ADDRESS,  # pub mkt fee token addr
    ]
    uints = [
        toBase18(DT_cap),
        toBase18(0.0),  # pub mkt fee amt
    ]
    _bytes: List[Any] = []

    tx = dataNFT.createERC20(
        erc20_template_index, strings, addresses, uints, _bytes, {"from": from_account}
    )
    DT_address = tx.events["TokenCreated"]["newTokenAddress"]
    DT = BROWNIE_PROJECT.ERC20Template.at(DT_address)

    return DT


@enforce_types
def deploySideStaking(from_account, router):
    return BROWNIE_PROJECT.SideStaking.deploy(router.address, {"from": from_account})


@enforce_types
def createBPoolFromDatatoken(
    datatoken,
    erc721_factory,
    from_account,
    init_OCEAN_liquidity=2000,
    DT_OCEAN_rate=0.1,
    DT_vest_amt=1000,
    DT_vest_num_blocks=600,
    LP_swap_fee=0.03,
    mkt_swap_fee=0.01,
): #pylint: disable=too-many-arguments

    OCEAN = OCEANtoken()
    pool_template = POOLTemplate()

    router_address = datatoken.router()
    router = BROWNIE_PROJECT.FactoryRouter.at(router_address)
    router.updateMinVestingPeriod(500, {"from": from_account})

    OCEAN.approve(
        router.address, toBase18(init_OCEAN_liquidity), {"from": from_account}
    )

    ssbot = deploySideStaking(from_account, router)
    router.addSSContract(ssbot.address, {"from": from_account})
    router.addFactory(erc721_factory.address, {"from": from_account})

    ss_params = [
        toBase18(1.0), #HACK toBase18(DT_OCEAN_rate),
        OCEAN.decimals(),
        toBase18(DT_vest_amt),
        DT_vest_num_blocks,  # do _not_ convert to wei
        toBase18(100.0), #HACK toBase18(init_OCEAN_liquidity),
    ]
    swap_fees = [
        toBase18(LP_swap_fee),
        toBase18(mkt_swap_fee),
    ]
    addresses = [
        ssbot.address,
        OCEAN.address,
        from_account.address,
        from_account.address,
        OPF_ADDRESS,
        pool_template.address,
    ]

    tx = datatoken.deployPool(ss_params, swap_fees, addresses, {"from": from_account})
    pool_address = poolAddressFromNewBPoolTx(tx)
    pool = BROWNIE_PROJECT.BPool.at(pool_address)

    return pool


@enforce_types
def poolAddressFromNewBPoolTx(tx):
    return tx.events["NewPool"]["poolAddress"]

#===============================================================================
#fee stuff needed for consume

#follow order in ocean.py/ocean_lib/structures/abi_tuples.py::ConsumeFees
def get_zero_consume_mkt_fee_tuple() -> Tuple:
    d = {
        "consumeMarketFeeAddress": ZERO_ADDRESS,
        "consumeMarketFeeToken": ZERO_ADDRESS,
        "consumeMarketFeeAmount": 0,
        }
    
    consume_mkt_fee = (
        d["consumeMarketFeeAddress"],
        d["consumeMarketFeeToken"],
        d["consumeMarketFeeAmount"],
    )
    return consume_mkt_fee

#follow order in ocean.py/ocean_lib/structures/abi_tuples.py::ProviderFees
def get_zero_provider_fee_tuple(pub_account) -> Tuple:
    d = get_zero_provider_fee_dict(pub_account)

    provider_fee = (
        d["providerFeeAddress"],
        d["providerFeeToken"],
        d["providerFeeAmount"],
        d["v"],
        d["r"],
        d["s"],
        d["validUntil"],
        d["providerData"],
        )

    return provider_fee

#from ocean.py/tests/resources/helper_functions.py
def get_zero_provider_fee_dict(provider_account) -> Dict[str, Any]:
    web3 = brownie.web3
    provider_fee_amount = 0
    compute_env = None
    provider_data = json.dumps({"environment": compute_env}, separators=(",", ":"))
    provider_fee_address = provider_account.address
    provider_fee_token = ZERO_ADDRESS
    valid_until = 0

    message = web3.solidityKeccak(
        ["bytes", "address", "address", "uint256", "uint256"],
        [
            web3.toHex(web3.toBytes(text=provider_data)),
            provider_fee_address,
            provider_fee_token,
            provider_fee_amount,
            valid_until,
        ],
    )
    signed = web3.eth.sign(provider_fee_address, data=message)
    signature = split_signature(signed)

    provider_fee = {
        "providerFeeAddress": provider_fee_address,
        "providerFeeToken": provider_fee_token,
        "providerFeeAmount": provider_fee_amount,
        "providerData": web3.toHex(web3.toBytes(text=provider_data)),
        # make it compatible with last openzepellin https://github.com/OpenZeppelin/openzeppelin-contracts/pull/1622
        "v": signature.v,
        "r": signature.r,
        "s": signature.s,
        "validUntil": 0,
    }

    return provider_fee

#from ocean.py/ocean_lib/web3_internal/utils.py
Signature = namedtuple("Signature", ("v", "r", "s"))

#from ocean.py/ocean_lib/web3_internal/utils.py
@enforce_types
def split_signature(signature: Any) -> Signature:
    """
    :param signature: signed message hash, hex str
    """
    web3 = brownie.web3
    assert len(signature) == 65, (
        f"invalid signature, " f"expecting bytes of length 65, got {len(signature)}"
    )
    v = web3.toInt(signature[-1])
    r = to_32byte_hex(int.from_bytes(signature[:32], "big"))
    s = to_32byte_hex(int.from_bytes(signature[32:64], "big"))
    if v != 27 and v != 28:
        v = 27 + v % 2

    return Signature(v, r, s)

#from ocean.py/ocean_lib/web3_internal/utils.py
@enforce_types
def to_32byte_hex(val: int) -> str:
    """

    :param val:
    :return:
    """
    web3 = brownie.web3
    return web3.toHex(web3.toBytes(val).rjust(32, b"\0"))
