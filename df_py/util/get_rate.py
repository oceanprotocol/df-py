import json
import os
from datetime import datetime, timedelta
from typing import Union

import requests
from enforce_typing import enforce_types

from df_py.util.blocktime import timestr_to_timestamp


@enforce_types
def get_rate(
    token_symbol: str, st: str, fin: str, target_currency="USDT", interval="1d"
) -> Union[float, None]:
    """
    @description
      Get the exchange rate for a token. Uses Binance. Coingecko is backup.

    @arguments
      token_symbol -- str -- e.g. "OCEAN" or "H2O"
      st -- start date in format "YYYY-MM-DD"
      fin -- end date

    @return
      rate -- float or None -- USD_per_token. None if failure
    """
    rate = get_binance_rate(token_symbol, st, fin, target_currency, interval)
    if rate is not None:
        return rate

    print("Couldn't get Binance data; trying CoinGecko")
    rate = get_coingecko_rate(token_symbol, st, fin)
    if rate is not None:
        return rate

    print("Couldn't get CoinGecko data. Returning None")
    return None


@enforce_types
def get_binance_rate(
    token_symbol: str, st: str, fin: str, target_currency="USDT", interval="1d"
) -> Union[float, None]:
    """
    @arguments
      token_symbol -- e.g. "OCEAN", "BTC"
      target_currency -- e.g. "USDT", "BTC"
      st -- start date in format "YYYY-MM-DD"
      st_time -- start time in hours (24-hour format), default is '00'
      st_min -- start time in minutes, default is '00'
      fin -- end date
      fin_time -- end time in hours (24-hour format), default is '00'
      fin_min -- end time in minutes, default is '00'
    @return
      rate -- float or None -- target_currency_per_token. None if failure
    """
    # corner case
    if token_symbol.upper() == "H2O":
        return 1.618
    data = get_binance_rate_all(token_symbol, st, fin, target_currency, interval)
    if not data:
        return None
    return sum(data) / len(data)
    


@enforce_types
def get_binance_rate_all(
    token_symbol: str, st: str, fin: str, target_currency="USDT", interval="1d"
) -> Union[float, None]:
    """
    @arguments
      token_symbol -- e.g. "OCEAN", "BTC"
      target_currency -- e.g. "USDT", "BTC"
      st -- start date in format "YYYY-MM-DD"
      st_time -- start time in hours (24-hour format), default is '00'
      st_min -- start time in minutes, default is '00'
      fin -- end date
      fin_time -- end time in hours (24-hour format), default is '00'
      fin_min -- end time in minutes, default is '00'
    @return
      rate -- float or None -- target_currency_per_token. None if failure
    """
    url = 'https://data.binance.com/api/v3/klines'
    st_dt = datetime.fromtimestamp(timestr_to_timestamp(st))
    fin_dt = datetime.fromtimestamp(timestr_to_timestamp(fin))

    num_days = (fin_dt - st_dt).days
    if num_days < 0:
        raise ValueError("Start date is after end date")

    start_time_unix = int(st_dt.timestamp())*1000
    end_time_unix = int(fin_dt.timestamp())*1000
    duration = end_time_unix - start_time_unix
    limit = 1000

    params = {
        'symbol': token_symbol + target_currency,
        'interval': interval,
        'startTime': start_time_unix,
        'endTime': end_time_unix,
        'limit': limit
    }
    try:
        res = requests.get(url, params=params, timeout=30)
        data = res.json()
        if not data:
            return None
        data = [float(x[4]) for x in data]
        return data
    # pylint: disable=broad-exception-caught
    except Exception as e:
        print(f"Error in get_binance_rate: {e}")
        return None

@enforce_types
def get_coingecko_rate(token_symbol: str, st: str, fin: str) -> Union[float, None]:
    """
    @arguments
      token_symbol -- e.g. "OCEAN", "BTC"
      st -- start date in format "YYYY-MM-DD"
      fin -- end date
    @return
      rate -- float or None -- USD_per_token. None if failure
    """
    # corner case
    if token_symbol.upper() == "H2O":
        return 1.618

    st_dt = datetime.fromtimestamp(timestr_to_timestamp(st))
    fin_dt = datetime.fromtimestamp(timestr_to_timestamp(fin))
    num_days = (fin_dt - st_dt).days
    if num_days < 0:
        raise ValueError("Start date is after end date")
    if num_days == 0:  # coingecko needs >=1 days of data
        st_dt = st_dt - timedelta(days=1)

    cg_id = _coingecko_id(token_symbol)
    if cg_id == "":
        raise ValueError(f"Couldn't find Coingecko ID for {token_symbol}")
    req_s = f"https://api.coingecko.com/api/v3/coins/{cg_id}/market_chart/range?vs_currency=usd&from={int(st_dt.timestamp())}&to={int(fin_dt.timestamp())}"  # pylint: disable=line-too-long
    print("URL", req_s)
    res = requests.get(req_s, timeout=30)
    data = res.json().get("prices")
    if not data:
        return None
    avg = sum([float(x[1]) for x in data]) / len(data)
    return avg


@enforce_types
def _coingecko_id(token_symbol: str) -> str:
    """Convert token_symbol to coingecko id for a few common tokens"""
    id_ = token_symbol.lower()

    all_tokens = None
    # Load json file from ./data/coingecko_ids.json relative to this file
    dirname = os.path.dirname(__file__)
    datapath = "../../data/coingecko_ids.json"
    filepath = os.path.join(dirname, datapath)
    with open(filepath, "r") as f:
        all_tokens = json.load(f)

    for token in all_tokens:
        if token["symbol"] == id_:
            return token["id"]

    return ""
