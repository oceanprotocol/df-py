import json
from typing import Dict, List, Tuple

import requests
from enforce_typing import enforce_types
from web3.main import Web3

from df_py.predictoor.queries import query_predictoor_contracts
from df_py.util import networkutil, oceanutil
from df_py.util.base18 import from_wei
from df_py.util.blockrange import BlockRange
from df_py.util.constants import AQUARIUS_BASE_URL, MAX_ALLOCATE
from df_py.util.contract_base import ContractBase
from df_py.util.graphutil import submit_query
from df_py.volume.models import SimpleDataNft, TokSet

MAX_TIME = 4 * 365 * 86400  # max lock time


@enforce_types
def queryVolsOwnersSymbols(
    rng: BlockRange, chainID: int
) -> Tuple[Dict[str, Dict[str, float]], Dict[str, str], Dict[str, str]]:
    """
    @description
      For given block range and chain, return each nft's {vols, owner, symbol}

    @return
      nftvols_at_chain -- dict of [nativetoken/basetoken_addr][nft_addr] : vol
      owners_at_chain -- dict of [nft_addr] : owner_addr
      symbols_at_chain -- dict of [basetoken_addr] : basetoken_symbol

    @notes
      A stake or nftvol value is denominated in basetoken (amt of OCEAN, H2O).
      Basetoken symbols are full uppercase, addresses are full lowercase.
    """
    Vi_unfiltered, Ci, gasvols = _queryVolsOwners(rng.st, rng.fin, chainID)
    swaps = _querySwaps(rng.st, rng.fin, chainID)
    Vi = _filterNftvols(Vi_unfiltered, chainID)
    Vi = _filterbyMaxVolume(Vi, swaps)

    # merge Vi and gasvols
    for basetoken in gasvols:
        if basetoken not in Vi:
            Vi[basetoken] = {}
        for nft in gasvols[basetoken]:
            if nft not in Vi[basetoken]:
                Vi[basetoken][nft] = 0.0
            Vi[basetoken][nft] += gasvols[basetoken][nft]

    # get all basetokens from Vi
    basetokens = TokSet()
    for basetoken in Vi:
        _symbol = symbol(rng.web3, basetoken)
        basetokens.add(chainID, basetoken, _symbol)
    SYMi = getSymbols(basetokens, chainID)
    return (Vi, Ci, SYMi)


@enforce_types
def _process_delegation(
    delegation, balance: float, unix_epoch_time: int, time_left_unlock: int
):
    """
    @description
      Process a single delegation
    @param
      delegation -- dict of delegation
      balance -- float of current balance
      unixEpochTime -- int of current block time
      timeLeftUnlock -- int of time for the users veOCEANs to be unlocked
    @return
      balance -- float of current balance
      delegation_amt -- float of amount delegated
      delegated_to -- str of address delegated to
    """
    if int(delegation["expireTime"]) < unix_epoch_time:
        return balance, 0, ""

    time_left_to_unlock_past = int(delegation["timeLeftUnlock"])
    delegated_amt_past = float(delegation["amount"])

    # amount of tokens delegated currently
    delegation_amt = time_left_unlock * delegated_amt_past / time_left_to_unlock_past

    # receiver address
    delegated_to = str(Web3.to_checksum_address(delegation["receiver"]["id"]))

    balance = balance - delegation_amt

    return balance, delegation_amt, delegated_to


@enforce_types
def queryVebalances(
    rng: BlockRange, CHAINID: int
) -> Tuple[Dict[str, float], Dict[str, float], Dict[str, int]]:
    """
    @description
      Return all ve balances

    @return
      vebals -- dict of [LP_addr] : veOCEAN_float
      locked_amt -- dict of [LP_addr] : locked_amt
      unlock_time -- dict of [LP_addr] : unlock_time
    """
    # [LP_addr] : veBalance
    vebals: Dict[str, float] = {}

    # [LP_addr] : locked_amt
    locked_amts: Dict[str, float] = {}

    # [LP_addr] : lock_time
    unlock_times: Dict[str, int] = {}

    web3 = networkutil.chain_id_to_web3(CHAINID)
    unixEpochTime = web3.eth.get_block("latest").timestamp
    n_blocks = rng.num_blocks()
    n_blocks_sampled = 0
    blocks = rng.get_blocks()
    print("queryVebalances: begin")

    for block_i, block in enumerate(blocks):
        if (block_i % 50) == 0 or (block_i == n_blocks - 1):
            print(f"  {(block_i+1) / float(n_blocks) * 100.0:.1f}% done")
        chunk_size = 1000
        offset = 0
        while True:
            query = """
              {
                veOCEANs(first: %d, skip: %d,block:{number: %d}) {
                  id
                  lockedAmount
                  unlockTime
                  delegation {
                    id
                    receiver {
                      id
                    }
                    amount
                    expireTime
                    timeLeftUnlock
                    lockedAmount
                    updates(orderBy:timestamp orderDirection:asc){
                      timestamp
                      sender
                      amount
                      type
                    }
                  }
                }
              }
            """ % (
                chunk_size,
                offset,
                block,
            )

            result = submit_query(query, CHAINID)
            if "data" in result:
                assert "veOCEANs" in result["data"]
                veOCEANs = result["data"]["veOCEANs"]
            else:
                return ({}, {}, {})

            if len(veOCEANs) == 0:
                # means there are no records left
                break

            for user in veOCEANs:
                ve_unlock_time = int(user["unlockTime"])
                time_left_to_unlock = (
                    ve_unlock_time - unixEpochTime
                )  # time left in seconds
                if time_left_to_unlock < 0:  # check if the lock has expired
                    continue

                # initial balance before accounting in delegations
                balance_init = (
                    float(user["lockedAmount"]) * time_left_to_unlock / MAX_TIME
                )

                # this will the balance after accounting in delegations
                # see the calculations below
                balance = balance_init

                for delegation in user["delegation"]:
                    balance, delegation_amt, delegated_to = _process_delegation(
                        delegation, balance, unixEpochTime, time_left_to_unlock
                    )

                    if delegation_amt == 0:
                        continue

                    vebals.setdefault(delegated_to, 0)
                    locked_amts.setdefault(delegated_to, 0)
                    unlock_times.setdefault(delegated_to, 0)
                    vebals[delegated_to] += delegation_amt

                if balance < 0:
                    raise ValueError("balance < 0, something is wrong")
                # set user balance
                LP_addr = str(Web3.to_checksum_address(user["id"]))
                vebals.setdefault(LP_addr, 0)
                vebals[LP_addr] += balance

                # set locked amount
                locked_amts[LP_addr] = float(user["lockedAmount"])

                # set unlock time
                unlock_times[LP_addr] = ve_unlock_time

            # increase offset
            offset += chunk_size
        n_blocks_sampled += 1

    # TODO: this assertion doesn't work with nsamples = 1, failing in test_queries all
    # assert n_blocks_sampled > 0

    # get average
    for LP_addr in vebals:
        vebals[LP_addr] /= n_blocks_sampled

    print("queryVebalances: done")

    return vebals, locked_amts, unlock_times


@enforce_types
def queryAllocations(
    rng: BlockRange, CHAINID: int
) -> Dict[int, Dict[str, Dict[str, float]]]:
    """
    @description
      Return all allocations.

    @return
      allocations -- dict of [chain_id][nft_addr][LP_addr]: percent
    """

    # [chain_id][nft_addr][LP_addr] : percent
    allocs: Dict[int, Dict[str, Dict[str, float]]] = {}

    n_blocks = rng.num_blocks()
    n_blocks_sampled = 0
    blocks = rng.get_blocks()

    for block_i, block in enumerate(blocks):
        if (block_i % 50) == 0 or (block_i == n_blocks - 1):
            print(f"  {(block_i+1) / float(n_blocks) * 100.0:.1f}% done")

        offset = 0
        chunk_size = 1000
        while True:
            query = """
          {
            veAllocateUsers(first: %d, skip: %d, block:{number:%d}) {
              id
              veAllocation {
                id
                allocated
                chainId
                nftAddress
              }
            }
          }
          """ % (
                chunk_size,
                offset,
                block,
            )
            result = submit_query(query, CHAINID)
            if "data" in result:
                assert "veAllocateUsers" in result["data"]
                _allocs = result["data"]["veAllocateUsers"]
            else:
                return {}

            if len(_allocs) == 0:
                # means there are no records left
                break

            for allocation in _allocs:
                LP_addr = str(Web3.to_checksum_address(allocation["id"]))
                for ve_allocation in allocation["veAllocation"]:
                    nft_addr = str(
                        Web3.to_checksum_address(ve_allocation["nftAddress"])
                    )
                    chain_id = int(ve_allocation["chainId"])
                    allocated = float(ve_allocation["allocated"])

                    if chain_id not in allocs:
                        allocs[chain_id] = {}
                    if nft_addr not in allocs[chain_id]:
                        allocs[chain_id][nft_addr] = {}

                    if LP_addr not in allocs[chain_id][nft_addr]:
                        allocs[chain_id][nft_addr][LP_addr] = allocated
                    else:
                        allocs[chain_id][nft_addr][LP_addr] += allocated

            offset += chunk_size
        n_blocks_sampled += 1

    # TODO: this assertion doesn't work with nsamples = 1, failing in test_queries all
    # assert n_blocks_sampled > 0

    # get average
    for chain_id in allocs:
        for nft_addr in allocs[chain_id]:
            for LP_addr in allocs[chain_id][nft_addr]:
                allocs[chain_id][nft_addr][LP_addr] /= n_blocks_sampled

    # get total allocs per each LP
    lp_total = {}
    for chain_id in allocs:
        for nft_addr in allocs[chain_id]:
            for LP_addr in allocs[chain_id][nft_addr]:
                if LP_addr not in lp_total:
                    lp_total[LP_addr] = 0.0
                lp_total[LP_addr] += allocs[chain_id][nft_addr][LP_addr]

    for LP_addr in lp_total:
        if lp_total[LP_addr] < MAX_ALLOCATE:
            lp_total[LP_addr] = MAX_ALLOCATE

    # normalize values per LP
    for chain_id in allocs:
        for nft_addr in allocs[chain_id]:
            for LP_addr in allocs[chain_id][nft_addr]:
                if lp_total[LP_addr] == 0.0:
                    print(f"WARNING: {lp_total[LP_addr]} == 0.0")
                    continue
                allocs[chain_id][nft_addr][LP_addr] /= lp_total[LP_addr]

    return allocs


@enforce_types
def queryNftinfo(chainID, endBlock="latest") -> List[SimpleDataNft]:
    """
    @description
      Fetch, filter and return all NFTs on the chain

    @return
      nftInfo -- list of SimpleDataNft objects
    """

    nftinfo = _queryNftinfo(chainID, endBlock)

    if chainID == networkutil.network_to_chain_id(
        "sapphire-mainnet"
    ) or chainID == networkutil.network_to_chain_id("sapphire-testnet"):
        opf_contracts = query_predictoor_contracts(chainID)
        nftinfo = _markPurgatoryNfts(nftinfo)
        nftinfo = [i for i in nftinfo if i.nft_addr in opf_contracts]
        for nft in nftinfo:
            nft.set_name("Predictoor Asset: " + opf_contracts[nft.nft_addr].name)

    elif chainID != networkutil.DEV_CHAINID:
        # filter if not on dev chain
        nftinfo = _filterNftinfos(nftinfo)
        nftinfo = _markPurgatoryNfts(nftinfo)
        nftinfo = _populateNftAssetNames(nftinfo)

    return nftinfo


@enforce_types
def _populateNftAssetNames(nftInfo: List[SimpleDataNft]) -> List[SimpleDataNft]:
    """
    @description
      Populate the list of NFTs with the asset names

    @return
      nftInfo -- list of SimpleDataNft objects
    """

    nft_dids = [nft.did for nft in nftInfo]
    did_to_name = queryAquariusAssetNames(nft_dids)

    for nft in nftInfo:
        nft.set_name(did_to_name[nft.did])

    return nftInfo


@enforce_types
def _queryNftinfo(chainID, endBlock) -> List[SimpleDataNft]:
    """
    @description
      Return all NFTs on the chain

    @return
      nftInfo -- list of SimpleDataNft objects
    """
    nftinfo = []
    chunk_size = 1000
    offset = 0

    if endBlock == "latest":
        w3 = networkutil.chain_id_to_web3(chainID)
        endBlock = w3.eth.get_block("latest").number

    while True:
        query = """
      {
         nfts(first: %d, skip: %d, block:{number:%d}) {
            id
            symbol
            owner {
              id
            }
        }
      }
      """ % (
            chunk_size,
            offset,
            endBlock,
        )
        result = submit_query(query, chainID)
        nft_records = result["data"]["nfts"]
        if len(nft_records) == 0:
            # means there are no records left
            break

        for nft_record in nft_records:
            nft_addr = nft_record["id"]
            _symbol = nft_record["symbol"]
            owner_addr = nft_record["owner"]["id"]
            simple_data_nft = SimpleDataNft(
                chain_id=chainID,
                nft_addr=nft_addr,
                _symbol=_symbol,
                owner_addr=owner_addr,
            )
            nftinfo.append(simple_data_nft)

        offset += chunk_size

    return nftinfo


@enforce_types
def _queryVolsOwners(
    st_block: int, end_block: int, chainID: int
) -> Tuple[Dict[str, Dict[str, float]], Dict[str, float], Dict[str, Dict[str, float]]]:
    """
    @description
      Query the chain for datanft volumes within the given block range.

    @return
      vols (at chain) -- dict of [nativetoken/basetoken_addr][nft_addr]:vol_amt
      owners (at chain) -- dict of [nft_addr]:vol_amt
    """
    print("_queryVolsOwners(): begin")

    vols: Dict[str, Dict[str, float]] = {}
    gasvols: Dict[str, Dict[str, float]] = {}
    owners: Dict[str, float] = {}
    txgascost: Dict[str, float] = {}  # tx hash : gas cost

    chunk_size = 1000  # max for subgraph = 1000
    offset = 0
    while True:
        query = """
        {
          orders(where: {block_gte:%s, block_lte:%s}, skip:%s, first:%s) {
            id,
            datatoken {
              id
              symbol
              nft {
                id
                owner{
                  id
                }
              }
              dispensers {
                id
              }
            },
            lastPriceToken{
              id
            },
            lastPriceValue,
            block,
            gasPrice,
            gasUsed,
            tx
          }
        }
        """ % (
            st_block,
            end_block,
            offset,
            chunk_size,
        )
        offset += chunk_size
        result = submit_query(query, chainID)
        if "errors" in result:
            raise AssertionError(result)
        new_orders = result["data"]["orders"]

        if new_orders == []:
            break
        for order in new_orders:
            lastPriceValue = float(order["lastPriceValue"])
            if len(order["datatoken"]["dispensers"]) == 0 and lastPriceValue == 0:
                continue
            basetoken_addr = order["lastPriceToken"]["id"].lower()
            nft_addr = order["datatoken"]["nft"]["id"].lower()
            owner_addr = order["datatoken"]["nft"]["owner"]["id"].lower()

            # add owner
            owners[nft_addr] = owner_addr

            # Calculate gas cost
            gasCostWei = int(order["gasPrice"]) * int(order["gasUsed"])

            # deduct 1 wei so it's not profitable for free assets
            gasCost = from_wei(gasCostWei - 1)
            native_token_addr = networkutil._CHAINID_TO_ADDRS[chainID].lower()

            # add gas cost value
            if gasCost > 0:
                if order["tx"] not in txgascost:
                    if native_token_addr not in gasvols:
                        gasvols[native_token_addr] = {}
                    if nft_addr not in gasvols[native_token_addr]:
                        gasvols[native_token_addr][nft_addr] = 0
                    txgascost[order["tx"]] = gasCost
                    gasvols[native_token_addr][nft_addr] += gasCost

            if lastPriceValue == 0:
                continue

            # add lastPriceValue
            if basetoken_addr not in vols:
                vols[basetoken_addr] = {}

            if nft_addr not in vols[basetoken_addr]:
                vols[basetoken_addr][nft_addr] = 0.0
            vols[basetoken_addr][nft_addr] += lastPriceValue

    print("_queryVolsOwners(): done")
    return (vols, owners, gasvols)


@enforce_types
def _querySwaps(
    st_block: int, end_block: int, chainID: int
) -> Dict[str, Dict[str, float]]:
    """
    @description
      Query the chain for datanft swaps within the given block range.

    @return
      vols (at chain) -- dict of [nativetoken/basetoken_addr][nft_addr]:vol_amt
      owners (at chain) -- dict of [nft_addr]:vol_amt
    """
    print("_querySwaps(): begin")

    # base token, nft addr, vol
    swaps: Dict[str, Dict[str, float]] = {}

    chunk_size = 1000  # max for subgraph = 1000
    offset = 0
    while True:
        query = """
        {
          fixedRateExchangeSwaps(where: {block_gte:%s, block_lte:%s}, skip:%s, first:%s) {
            id
            baseTokenAmount
            block
            exchangeId {
              id
              baseToken {
                id
              }
              datatoken {
                id
                symbol
                nft {
                  id
                }
              }
            }
          }
        }
        """ % (
            st_block,
            end_block,
            offset,
            chunk_size,
        )
        offset += chunk_size
        result = submit_query(query, chainID)
        if "errors" in result:
            raise AssertionError(result)
        new_swaps = result["data"]["fixedRateExchangeSwaps"]
        if new_swaps == []:
            break
        for swap in new_swaps:
            amt = float(swap["baseTokenAmount"])
            if amt == 0:
                continue
            nft_addr = swap["exchangeId"]["datatoken"]["nft"]["id"].lower()
            basetoken_addr = swap["exchangeId"]["baseToken"]["id"].lower()
            if basetoken_addr not in swaps:
                swaps[basetoken_addr] = {}
            if nft_addr not in swaps[basetoken_addr]:
                swaps[basetoken_addr][nft_addr] = 0.0
            swaps[basetoken_addr][nft_addr] += amt

    print("_querySwaps(): done")
    return swaps


@enforce_types
def queryPassiveRewards(
    chain_id: int,
    timestamp: int,
    addresses: List[str],
) -> Tuple[Dict[str, float], Dict[str, float]]:
    """
    @description
      Query the chain for passive rewards at the given timestamp.

    @params
      timestamp -- timestamp to query
      addresses -- list of addresses to query

    @return
      balances -- dict of [addr]:balance
      rewards -- dict of [addr]:reward_amt
    """
    print("getPassiveRewards(): begin")
    rewards: Dict[str, float] = {}
    balances: Dict[str, float] = {}

    fee_distributor = oceanutil.FeeDistributor(chain_id)
    ve_supply = fee_distributor.ve_supply(timestamp)
    total_rewards = fee_distributor.tokens_per_week(timestamp)
    ve_supply_float = from_wei(ve_supply)
    total_rewards_float = from_wei(total_rewards)

    if ve_supply_float == 0:
        return balances, rewards

    for addr in addresses:
        balance = fee_distributor.ve_for_at(addr, timestamp)
        balance_float = from_wei(balance)
        balances[addr] = balance_float
        rewards[addr] = total_rewards_float * balance_float / ve_supply_float

    print("getPassiveRewards(): done")
    return balances, rewards


@enforce_types
def _filterDids(nft_dids: List[str]) -> List[str]:
    """
    @description
      Filter out DIDs that are in purgatory and are not in Aquarius
    """
    nft_dids = _filterOutPurgatory(nft_dids)
    nft_dids = _filterToAquariusAssets(nft_dids)
    return nft_dids


@enforce_types
def _filterOutPurgatory(nft_dids: List[str]) -> List[str]:
    """
    @description
      Return dids that aren't in purgatory

    @arguments
      nft_dids: list of dids

    @return
      filtered_dids: list of filtered dids
    """
    bad_dids = _didsInPurgatory()
    filtered_dids = set(nft_dids) - set(bad_dids)
    return list(filtered_dids)


@enforce_types
def _filterNftinfos(nftinfos: List[SimpleDataNft]) -> List[SimpleDataNft]:
    """
    @description
      Filter out NFTs that are in purgatory and are not in Aquarius

    @arguments
      nftinfos: list of SimpleDataNft objects

    @return
      filtered_nftinfos: list of filtered SimpleDataNft objects
    """
    nft_dids = [nft.did for nft in nftinfos]
    nft_dids = _filterToAquariusAssets(nft_dids)
    filtered_nftinfos = [nft for nft in nftinfos if nft.did in nft_dids]
    return filtered_nftinfos


@enforce_types
def _markPurgatoryNfts(nftinfos: List[SimpleDataNft]) -> List[SimpleDataNft]:
    bad_dids = _didsInPurgatory()
    for nft in nftinfos:
        if nft.did in bad_dids:
            nft.is_purgatory = True
    return nftinfos


@enforce_types
def _filterbyMaxVolume(nftvols: dict, swaps: dict) -> dict:
    for basetoken in nftvols:
        for nftaddr in nftvols[basetoken]:
            if not basetoken in swaps:
                nftvols[basetoken][nftaddr] = 0
                continue
            if not nftaddr in swaps[basetoken]:
                nftvols[basetoken][nftaddr] = 0
                continue
            nftvols[basetoken][nftaddr] = min(
                nftvols[basetoken][nftaddr], swaps[basetoken][nftaddr]
            )
    return nftvols


@enforce_types
def _filterNftvols(nftvols: dict, chainID: int) -> dict:
    """
    @description
      For remote chains: filters out nfts in purgatory & not in Aquarius
      For dev chain, filters out '0xdevelopment' basetoken (hinders tests).

    @arguments
      nftvols: dict of [basetoken_addr][nft_addr]:vol_amt
      chainID: int

    @return
      filtered_nftvols: list of [basetoken_addr][nft_addr]:vol_amt
    """
    if chainID == networkutil.DEV_CHAINID:
        nftvols2 = {
            basetoken: nftvols[basetoken]
            for basetoken in nftvols.keys()
            if basetoken != "0xdevelopment"
        }
        return nftvols2

    if chainID == networkutil.network_to_chain_id(
        "sapphire-mainnet"
    ) or chainID == networkutil.network_to_chain_id("sapphire-testnet"):
        # aquarius is not deployed on Sapphire
        # get all assets deployed by OPF
        opf_contracts = query_predictoor_contracts(chainID)

        filtered_nftvols_predictoor: Dict[str, Dict[str, float]] = {}

        for basetoken_addr in nftvols:
            for nft_addr in nftvols[basetoken_addr]:
                if nft_addr not in opf_contracts:
                    continue
                if basetoken_addr not in filtered_nftvols_predictoor:
                    filtered_nftvols_predictoor[basetoken_addr] = {}
                filtered_nftvols_predictoor[basetoken_addr][nft_addr] = nftvols[
                    basetoken_addr
                ][nft_addr]
        return filtered_nftvols_predictoor

    filtered_nftvols: Dict[str, Dict[str, float]] = {}
    nft_dids = []

    for basetoken_addr in nftvols:
        for nft_addr in nftvols[basetoken_addr]:
            nft_dids.append(oceanutil.calc_did(nft_addr, chainID))

    filtered_dids = _filterDids(nft_dids)

    for basetoken_addr in nftvols:
        for nft_addr in nftvols[basetoken_addr]:
            did = oceanutil.calc_did(nft_addr, chainID)
            if did in filtered_dids:
                if basetoken_addr not in filtered_nftvols:
                    filtered_nftvols[basetoken_addr] = {}
                filtered_nftvols[basetoken_addr][nft_addr] = nftvols[basetoken_addr][
                    nft_addr
                ]

    return filtered_nftvols


@enforce_types
def _filterToAquariusAssets(nft_dids: List[str]) -> List[str]:
    """
    @description
      Filter a list of nft_dids to only those that are in Aquarius

    @arguments
      nft_dids: list of nft_dids

    @return
      filtered_dids: list of filtered nft_dids
    """
    filtered_nft_dids = []

    assets = queryAquariusAssetNames(nft_dids)

    # Aquarius returns "" as the name for assets that isn't in the marketplace
    for did in assets:
        if assets[did] != "":
            filtered_nft_dids.append(did)

    return filtered_nft_dids


@enforce_types
def _didsInPurgatory() -> List[str]:
    """
    @description
      Return dids of data assets that are in purgatory

    @return
      dids -- list of str
    """
    url = "https://raw.githubusercontent.com/oceanprotocol/list-purgatory/main/list-assets.json"
    resp = requests.get(url, timeout=30)

    # list of {'did' : 'did:op:6F7...', 'reason':'..'}
    data = json.loads(resp.text)

    dids = [item["did"] for item in data]
    return dids


@enforce_types
def getSymbols(tokens: TokSet, chainID: int) -> Dict[str, str]:
    """
    @description
      Return mapping of basetoken addr -> symbol for this chain

    @return
      symbols_at_chain -- dict of [basetoken_addr] : basetoken_symbol
    """
    return {tok.address: tok.symbol for tok in tokens.toks if tok.chainID == chainID}


_ADDR_TO_SYMBOL = networkutil._ADDRS_TO_SYMBOL  # address : TOKEN_symbol


@enforce_types
def symbol(web3, addr: str):
    """Returns token symbol, given its address."""
    global _ADDR_TO_SYMBOL
    if addr not in _ADDR_TO_SYMBOL:
        _symbol = ContractBase(web3, "OceanToken", addr).symbol()
        _symbol = _symbol.upper()  # follow lower-upper rules
        _ADDR_TO_SYMBOL[addr] = _symbol
    return _ADDR_TO_SYMBOL[addr]


@enforce_types
def queryAquariusAssetNames(
    nft_dids: List[str],
) -> Dict[str, str]:
    """
    @description
      Return mapping of did -> asset name

    @params
      nft_dids -- array of dids

    @return
      did_to_asset_name -- dict of [did] : asset_name
    """

    # Remove duplicates
    nft_dids = list(set(nft_dids))

    # make a post request to Aquarius
    url = f"{AQUARIUS_BASE_URL}/api/aquarius/assets/names"

    headers = {"Content-Type": "application/json"}

    did_to_asset_name = {}

    BATCH_SIZE = 9042
    RETRY_ATTEMPTS = 3

    error_counter = 0
    # Send in chunks
    for i in range(0, len(nft_dids), BATCH_SIZE):
        # Aquarius expects "didList": ["did:op:...", ...]
        payload = json.dumps({"didList": nft_dids[i : i + BATCH_SIZE]})

        try:
            resp = requests.post(url, data=payload, headers=headers, timeout=30)
            data = json.loads(resp.text)
            did_to_asset_name.update(data)
        # pylint: disable=broad-exception-caught
        except Exception as e:
            error_counter += 1
            i -= BATCH_SIZE
            if error_counter > RETRY_ATTEMPTS:
                # pylint: disable=line-too-long, broad-exception-raised
                raise Exception(
                    f"Failed to get asset names from Aquarius after {RETRY_ATTEMPTS} attempts. Error: {e}"
                ) from e
        error_counter = 0

    return did_to_asset_name
