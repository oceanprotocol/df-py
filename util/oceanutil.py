from collections import namedtuple
import hashlib
import json
from typing import Any, Dict, List, Tuple

import random
import brownie
from enforce_typing import enforce_types

from util import networkutil
from util.base18 import fromBase18, toBase18
from util.constants import BROWNIE_PROJECT as B, CONTRACTS, ZERO_ADDRESS


@enforce_types
def _contracts(key: str):
    """Returns the contract object at the currently connected network"""
    chainID = brownie.network.chain.id
    return CONTRACTS[chainID][key]


@enforce_types
def recordDevDeployedContracts():
    assert brownie.network.is_connected()
    assert brownie.network.chain.id == networkutil.DEV_CHAINID
    address_file = networkutil.chainIdToAddressFile(networkutil.DEV_CHAINID)
    recordDeployedContracts(address_file)


@enforce_types
def recordDeployedContracts(address_file: str):
    """Records deployed Ocean contracts at currently connected network"""
    assert brownie.network.is_connected()
    chainID = brownie.network.chain.id

    if chainID in CONTRACTS:  # already filled
        return

    network = networkutil.chainIdToNetwork(chainID)
    with open(address_file, "r") as json_file:
        a = json.load(json_file)[network]  # dict of contract_name: address

    C = {}
    C["Ocean"] = B.Simpletoken.at(a["Ocean"])
    C["ERC721Template"] = B.ERC721Template.at(a["ERC721Template"]["1"])
    C["ERC20Template"] = B.ERC20Template.at(a["ERC20Template"]["1"])
    C["PoolTemplate"] = B.BPool.at(a["poolTemplate"])
    C["Router"] = B.FactoryRouter.at(a["Router"])
    C["Staking"] = B.SideStaking.at(a["Staking"])
    C["ERC721Factory"] = B.ERC721Factory.at(a["ERC721Factory"])
    C["FixedPrice"] = B.FixedRateExchange.at(a["FixedPrice"])
    C["veOCEAN"] = B.veOCEAN.at(a["veOCEAN"])
    C["veAllocate"] = B.veAllocate.at(a["veAllocate"])

    CONTRACTS[chainID] = C


def OCEANtoken():
    return _contracts("Ocean")


def OCEAN_address() -> str:
    return OCEANtoken().address.lower()


def ERC721Template():
    return _contracts("ERC721Template")


def ERC20Template():
    return _contracts("ERC20Template")


def PoolTemplate():
    return _contracts("PoolTemplate")


def factoryRouter():
    return _contracts("Router")


def Staking():
    return _contracts("Staking")


def ERC721Factory():
    return _contracts("ERC721Factory")


def veOCEAN():
    return _contracts("veOCEAN")


def veAllocate():
    return _contracts("veAllocate")


def FixedPrice():
    return _contracts("FixedPrice")


@enforce_types
def createDataNFT(name: str, symbol: str, from_account):
    erc721_factory = ERC721Factory()
    template_index = 1
    additional_metadata_updater = ZERO_ADDRESS
    additional_erc20_deployer = factoryRouter().address
    transferable = True
    owner = from_account.address
    token_uri = "https://mystorage.com/mytoken.png"

    tx = erc721_factory.deployERC721Contract(
        name,
        symbol,
        template_index,
        additional_metadata_updater,
        additional_erc20_deployer,
        token_uri,
        transferable,
        owner,
        {"from": from_account},
    )
    data_NFT_address = tx.events["NFTCreated"]["newTokenAddress"]
    data_NFT = B.ERC721Template.at(data_NFT_address)
    return data_NFT


@enforce_types
def createDatatokenFromDataNFT(DT_name: str, DT_symbol: str, data_NFT, from_account):

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
        toBase18(1.0),  # cap. Note contract will hardcod this to max_int
        toBase18(0.0),  # pub mkt fee amt
    ]
    _bytes: List[Any] = []

    tx = data_NFT.createERC20(
        erc20_template_index, strings, addresses, uints, _bytes, {"from": from_account}
    )
    DT_address = tx.events["TokenCreated"]["newTokenAddress"]
    DT = B.ERC20Template.at(DT_address)

    return DT


@enforce_types
def createFREFromDatatoken(
    datatoken,
    base_TOKEN,
    amount,
    from_account,
):
    datatoken.approve(FixedPrice().address, toBase18(amount), {"from": from_account})

    addresses = [
        base_TOKEN.address,  # baseToken
        from_account.address,  # owner
        from_account.address,  # marketFeeCollector address
        ZERO_ADDRESS,  # allowed swapper
    ]

    uints = [
        base_TOKEN.decimals(),  # baseTokenDecimals
        datatoken.decimals(),  # datatokenDecimals
        toBase18(1.0),  # fixedRate
        0,  # marketFee
        0,  # withMint
    ]

    tx = datatoken.createFixedRate(
        FixedPrice().address, addresses, uints, {"from": from_account}
    )
    exchangeId = _FREAddressFromNewFRETx(tx)

    return exchangeId


@enforce_types
def _FREAddressFromNewFRETx(tx) -> str:
    return tx.events["NewFixedRate"]["exchangeId"]


@enforce_types
def randomCreateFREs(num_FRE: int, base_token, accounts):
    # create random num_FRE.
    tups = []  # (pub_account_i, data_NFT, DT, exchangeId)
    for fre_i in range(num_FRE):
        if fre_i < len(accounts):
            account_i = fre_i
        else:
            account_i = random.randint(0, len(accounts))
        (data_NFT, DT, exchangeId) = createDataNFTWithFRE(
            accounts[account_i], base_token
        )
        tups.append((account_i, data_NFT, DT, exchangeId))

    return tups


@enforce_types
def createDataNFTWithFRE(from_account, token):
    data_NFT = createDataNFT("1", "1", from_account)
    DT = createDatatokenFromDataNFT("1", "1", data_NFT, from_account)

    exchangeId = createFREFromDatatoken(DT, token, 10.0, from_account)
    return (data_NFT, DT, exchangeId)


@enforce_types
def createBPoolFromDatatoken(
    datatoken,
    base_TOKEN,
    from_account,
    init_TOKEN_liquidity: float = 2000.0,
    DT_TOKEN_rate: float = 0.1,
    LP_swap_fee: float = 0.03,
    mkt_swap_fee: float = 0.01,
):
    TOK_have = fromBase18(base_TOKEN.balanceOf(from_account))
    TOK_need = init_TOKEN_liquidity
    TOK_name = base_TOKEN.symbol()
    assert TOK_have >= TOK_need, f"have {TOK_have} {TOK_name}, need {TOK_need}"

    pool_template = PoolTemplate()
    router = factoryRouter()  # router.routerOwner() = '0xe2DD..' = accounts[0]
    ssbot = Staking()

    base_TOKEN.approve(
        router.address, toBase18(init_TOKEN_liquidity), {"from": from_account}
    )

    # dummy values since vestin is now turned off
    DT_vest_amt: float = 1000.0
    DT_vest_num_blocks: int = 2426000

    ss_params = [
        toBase18(DT_TOKEN_rate),  # rate (wei)
        base_TOKEN.decimals(),  # baseToken (decimals)
        toBase18(DT_vest_amt),  # vesting amount (wei)
        DT_vest_num_blocks,  # vested blocks (int, *not* wei)
        toBase18(init_TOKEN_liquidity),  # initial liquidity (wei)
    ]
    swap_fees = [
        toBase18(LP_swap_fee),  # swap fee for LPs (wei)
        toBase18(mkt_swap_fee),  # swap fee for marketplace runner (wei)
    ]
    addresses = [
        ssbot.address,  # ssbot address
        base_TOKEN.address,  # baseToken address
        from_account.address,  # baseTokenSender, provides init baseToken liquidity
        from_account.address,  # publisherAddress, will get the vested amt
        from_account.address,  # marketFeeCollector address
        pool_template.address,  # poolTemplate address
    ]

    tx = datatoken.deployPool(ss_params, swap_fees, addresses, {"from": from_account})
    pool_address = _poolAddressFromNewBPoolTx(tx)
    pool = B.BPool.at(pool_address)

    return pool


@enforce_types
def _poolAddressFromNewBPoolTx(tx) -> str:
    return tx.events["NewPool"]["poolAddress"]


# ===============================================================================
# fee stuff needed for consume

# follow order in ocean.py/ocean_lib/structures/abi_tuples.py::ConsumeFees
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


# follow order in ocean.py/ocean_lib/structures/abi_tuples.py::ProviderFees
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


# from ocean.py/tests/resources/helper_functions.py
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
        # make it compatible with last openzepellin
        # https://github.com/OpenZeppelin/openzeppelin-contracts/pull/1622
        "v": signature.v,
        "r": signature.r,
        "s": signature.s,
        "validUntil": 0,
    }

    return provider_fee


# from ocean.py/ocean_lib/web3_internal/utils.py
Signature = namedtuple("Signature", ("v", "r", "s"))

# from ocean.py/ocean_lib/web3_internal/utils.py
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


# from ocean.py/ocean_lib/web3_internal/utils.py
@enforce_types
def to_32byte_hex(val: int) -> str:
    """

    :param val:
    :return:
    """
    web3 = brownie.web3
    return web3.toHex(web3.toBytes(val).rjust(32, b"\0"))


@enforce_types
def calcDID(nft_addr: str, chainID: int) -> str:
    nft_addr2 = brownie.web3.toChecksumAddress(nft_addr)

    # adapted from ocean.py/ocean_lib/ocean/ocean_assets.py
    did = f"did:op:{create_checksum(nft_addr2 + str(chainID))}"
    return did


# from ocean.py/ocean_lib/utils/utilities.py
@enforce_types
def create_checksum(text: str) -> str:
    """
    :return: str
    """
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def set_allocation(amount: float, nft_addr: str, chainID: int, from_account):
    veAllocate().setAllocation(amount, nft_addr, chainID, {"from": from_account})
