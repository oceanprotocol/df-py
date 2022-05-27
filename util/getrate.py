from datetime import datetime
import requests


def getrate(token_symbol: str, st: str, fin: str) -> float:
    """
    @description
      Get the exchange rate for a token.
      Takes one measure per day. Averages across each day.
      Max 40 days, since Coingecko API rate-limits to 50 calls/min.

    @arguments
      token_symbol -- str -- e.g. "OCEAN" or "H2O"
      st -- start date in format "YYYY-MM-DD"
      fin -- end date in format "YYYY-MM-DD"

    @return
      rate -- float -- USD_per_token
    """
    # corner case
    # if token_symbol.lower() == "h2o":
    #     return 1.618  # target peg. Update this when H2O is on coingecko

    st_dt = datetime.strptime(st, "%Y-%m-%d")
    fin_dt = datetime.strptime(fin, "%Y-%m-%d")
    num_days = (fin_dt - st_dt).days
    if num_days < 0:
        raise ValueError("Start date is after end date")

    try:
        return binanceRate(token_symbol, st_dt, fin_dt)
    # pylint: disable=broad-except
    except Exception as e:
        print("An error occured while fetching price from Binance, trying CoinGecko", e)
        try:
            return coingeckoRate(token_symbol, st_dt, fin_dt)
        # pylint: disable=broad-except
        except Exception as ee:
            if token_symbol.lower() == "h2o":
                print("An error occured while fetching price from CoinGecko", ee)
                return 1.618
            raise Exception(f"Could not get the rate for {token_symbol} {ee}")


def binanceRate(token_symbol: str, st_dt: datetime, fin_dt: datetime) -> float:
    # pylint: disable=line-too-long
    res = requests.get(
        f"https://api.binance.com/api/v3/klines?symbol={token_symbol}USDT&interval=1d&startTime={int(st_dt.timestamp())*1000}&endTime={int(fin_dt.timestamp())*1000}"
    )
    data = res.json()
    avg = sum([float(x[4]) for x in data]) / len(data)
    return avg


def coingeckoRate(token_symbol: str, st_dt: datetime, fin_dt: datetime) -> float:
    """
    @arguments
      token_symbol -- e.g. "OCEAN", "BTC"
      timestr -- str in format "YYYY-MM-DD"
    @return
      rate -- float -- USD_per_token
    """
    cg_id = _coingeckoId(token_symbol)
    # pylint: disable=line-too-long
    res = requests.get(
        f"https://api.coingecko.com/api/v3/coins/{cg_id}/market_chart/range?vs_currency=usd&from={int(st_dt.timestamp())}&to={int(fin_dt.timestamp())}"
    )
    data = res.json()["prices"]
    avg = sum([float(x[1]) for x in data]) / len(data)
    return avg


def _coingeckoId(token_symbol: str) -> str:
    """Convert token_symbol to coingecko id for a few common tokens"""
    id_ = token_symbol.lower()
    if id_ == "btc":
        return "bitcoin"
    if "ocean" in id_:
        return "ocean-protocol"
    return id_


## NOT USED
# def getUniswapRate(pool_addr: str, twap_interval_seconds: int):
#     infura_url = os.getenv("ETH_RPC_URL")
#     web3 = Web3(Web3.HTTPProvider(infura_url))
#     abi = '[{"inputs":[{"internalType":"uint32[]","name":"secondsAgos","type":"uint32[]"}],"name":"observe","outputs":[{"internalType":"int56[]","name":"tickCumulatives","type":"int56[]"},{"internalType":"uint160[]","name":"secondsPerLiquidityCumulativeX128s","type":"uint160[]"}],"stateMutability":"view","type":"function"},{"inputs":[],"name":"slot0","outputs":[{"internalType":"uint160","name":"sqrtPriceX96","type":"uint160"},{"internalType":"int24","name":"tick","type":"int24"},{"internalType":"uint16","name":"observationIndex","type":"uint16"},{"internalType":"uint16","name":"observationCardinality","type":"uint16"},{"internalType":"uint16","name":"observationCardinalityNext","type":"uint16"},{"internalType":"uint8","name":"feeProtocol","type":"uint8"},{"internalType":"bool","name":"unlocked","type":"bool"}],"stateMutability":"view","type":"function"}]'
#     contract = web3.eth.contract(address=pool_addr, abi=abi)

#     if twap_interval_seconds == 0:
#         raise Exception("Interval cannot be 0 seconds")

#     # twap interval - before
#     # 0 - after (now)
#     before_after = [twap_interval_seconds, 0]

#     tick_cumulatives, _ = contract.functions.observe(before_after).call()
#     print(tick_cumulatives)

#     avg_tick = abs((tick_cumulatives[1] - tick_cumulatives[0]) / twap_interval_seconds)
#     price = 1.0001**avg_tick
#     return price
