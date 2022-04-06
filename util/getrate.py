from enforce_typing import enforce_types

def getrate(token_symbol:str, st:str, fin:str, nsamp:int, seed:int) -> float:
    """
    @description
      Get the exchange rate for a token, averaged over a time period

    @arguments
      token_symbol -- str -- e.g. "OCEAN" or "H2O"
      st -- str -- start time, in format YYYY-MM-DD | YYYY-MM-DD_HH:MM
      fin -- str -- end time, in format YYYY-MM-DD | YYYY-MM-DD_HH:MM | now
      nsamp -- int -- # times to randomly sample from in the time rnage
      seed -- int -- random seed 
    
    @return
      rates -- float -- USD_per_token
    """
    raise NotImplementedError()
