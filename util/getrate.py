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
            raise Exception(f"Could not get the rate for {token_symbol}") from ee


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
