from datetime import datetime, timedelta
import numpy
from pycoingecko import CoinGeckoAPI


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
    if token_symbol.lower() == "h2o":
        return 1.618  # target peg. Update this when H2O is on coingecko

    st_dt = datetime.strptime(st, "%Y-%m-%d")
    fin_dt = datetime.strptime(fin, "%Y-%m-%d")
    num_days = (fin_dt - st_dt).days
    if num_days < 0:
        raise ValueError("Start date is after end date")
    if num_days > 40:
        raise ValueError("max 40 days, since coingecko rate-limits")

    rates = []
    for day_i in range(num_days + 1):
        dt = st_dt + timedelta(days=day_i)
        timestr = f"{dt.year:04d}-{dt.month:02d}-{dt.day:02d}"
        rate_day = coingeckoRate(token_symbol, timestr)
        rates.append(rate_day)

    rate = numpy.average(rates)
    return float(rate)


def coingeckoRate(token_symbol: str, timestr: str) -> float:
    """
    @arguments
      token_symbol -- e.g. "OCEAN", "BTC"
      timestr -- str in format "YYYY-MM-DD"
    @return
      rate -- float -- USD_per_token
    """
    cg_id = _coingeckoId(token_symbol)
    cg_date = _coingeckoDate(timestr)

    cg = CoinGeckoAPI()
    result = cg.get_coin_history_by_id(id=cg_id, date=cg_date)
    rate = result["market_data"]["current_price"]["usd"]
    return rate


def _coingeckoId(token_symbol: str) -> str:
    """Convert token_symbol to coingecko id for a few common tokens"""
    id_ = token_symbol.lower()
    if id_ == "btc":
        return "bitcoin"
    if "ocean" in id_:
        return "ocean-protocol"
    return id_


def _coingeckoDate(timestr: str) -> str:
    """
    @arguments
      timestr -- str in format "YYYY-MM-DD"
    @return
      coingecko_date -- str in format "DD-MM-YYYY"
    """
    dt = datetime.strptime(timestr, "%Y-%m-%d")
    return f"{dt.day:02d}-{dt.month:02d}-{dt.year:04d}"
