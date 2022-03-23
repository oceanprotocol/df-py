from collections import namedtuple
from enforce_typing import enforce_types
import json
from typing import Any, List, Dict, Tuple

import brownie

from util.base18 import toBase18
from util.constants import BROWNIE_PROJECT, GOD_ACCOUNT, ZERO_ADDRESS

CONTRACTS = {}
def _contracts(key):
    global CONTRACTS
    return CONTRACTS[key]
    
def recordDeployedContracts(address_file, network):
    with open(address_file, 'r') as json_file:
        a = json.load(json_file)[network] #dict of contract_name: address
        
    global CONTRACTS
    assert CONTRACTS == {}
    B, C = BROWNIE_PROJECT, CONTRACTS
    C["Ocean"] = B.Simpletoken.at(a["Ocean"])
    C["ERC721Template"] = B.ERC721Template.at(a["ERC721Template"]["1"])
    C["ERC20Template"] = B.ERC20Template.at(a["ERC20Template"]["1"])
    C["PoolTemplate"] = B.BPool.at(a["poolTemplate"])
    C["Router"] = B.FactoryRouter.at(a["Router"])
    C["ERC721Factory"] = B.ERC721Factory.at(a["ERC721Factory"])

def OCEANtoken():
    return _contracts("Ocean")

def OCEAN_address() -> str:
    return OCEANtoken().address

def fundOCEANFromAbove(dst_address: str, amount_base: int):
    OCEANtoken().transfer(dst_address, amount_base, {"from": GOD_ACCOUNT})
    
def ERC721Template():
    return _contracts("ERC721Template")

def ERC20Template():
    return _contracts("ERC20Template")

def PoolTemplate():
    return _contracts("PoolTemplate")

def factoryRouter():
    return _contracts("Router")

def ERC721Factory():
    return _contracts("ERC721Factory")

@enforce_types
def createDataNFT(name: str, symbol: str, from_account):
    erc721_factory = ERC721Factory()
    erc721_template_index = 1
    factory_router = factoryRouter()
    token_URI = "https://mystorage.com/mytoken.png"
    tx = erc721_factory.deployERC721Contract(
        name,
        symbol,
        erc721_template_index,
        factory_router.address,
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


def deploySideStaking(from_account):
    factory_router = factoryRouter()
    return BROWNIE_PROJECT.SideStaking.deploy(factory_router.address, {"from": from_account})


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
    pool_template = PoolTemplate()
    router = factoryRouter() #router.routerOwner() = '0xe2DD..' = accounts[0]
    #router.updateMinVestingPeriod(500, {"from": from_account})
    router.updateMinVestingPeriod(500, {"from": GOD_ACCOUNT})

    OCEAN.approve(
        router.address, toBase18(init_OCEAN_liquidity), {"from": from_account}
    )

    ssbot = deploySideStaking(from_account)
    router.addSSContract(ssbot.address, {"from": from_account})
    #router.addSSContract(ssbot.address, {"from": GOD_ACCOUNT})

    ss_params = [
        toBase18(DT_OCEAN_rate),
        OCEAN.decimals(),
        toBase18(DT_vest_amt),
        DT_vest_num_blocks,  # do _not_ convert to wei
        toBase18(init_OCEAN_liquidity),
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
        from_account.address,
        pool_template.address,
    ]

    tx = datatoken.deployPool(
        ss_params, swap_fees, addresses, {"from": from_account})
    pool_address = poolAddressFromNewBPoolTx(tx)
    pool = BROWNIE_PROJECT.BPool.at(pool_address)

    return pool


def poolAddressFromNewBPoolTx(tx):
    return tx.events["NewPool"]["poolAddress"]

#===============================================================================
#fee stuff needed for consume

#follow order in ocean.py/ocean_lib/structures/abi_tuples.py::ConsumeFees
@enforce_types
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
@enforce_types
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
@enforce_types
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
