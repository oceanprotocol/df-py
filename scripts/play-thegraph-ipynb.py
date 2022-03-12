#taken from https://github.com/danielzak/thegraph-intro/blob/main/0.1-Intro.ipynb
# with comments in https://forum.thegraph.com/t/getting-started-with-subgraph-data-in-python/2130 

# step 1 - imports 
import requests
import json
import numpy as np

from datetime import datetime
import matplotlib.pyplot as plt

# step 2 - subgraph data
# Subgraph ID: QmWTrJJ9W8h3JE19FhCzzPYsJ2tgXZCdUqnbyuo64ToTBN
# Subgraph URL: https://api.thegraph.com/subgraphs/name/uniswap/uniswap-v2

# Data generated from TheGraph Uniswap v2 public, hosted API at https://thegraph.com/explorer/subgraph/uniswap/uniswap-v2
# Token ID for WETH: 0xc02aaa39b223fe8d0a0e5c4f27ead9083c756cc2
# Token ID for WBTC: 0x2260fac5e5542a773aa44fbcfedf7c193bc2c599
# Token ID for OCEAN: 0x967da4048cd07ab37855c090aaf366e4ce1b9f48

# Sample GraphQL query:
# Daily price data for WETH in USD. Change the token ID e.g. to WBTC above to test another token.

query = """query {
    tokenDayDatas(first:1000, where: {token: "0xc02aaa39b223fe8d0a0e5c4f27ead9083c756cc2"}, orderBy: date, orderDirection: desc) {
      date
      priceUSD
    }
}"""

# Call the public hosted TheGraph endpoint
url = 'https://api.thegraph.com/subgraphs/name/uniswap/uniswap-v2'
r = requests.post(url, json={'query': query})
print(r.status_code)

# step 3 - save data to Numpy array
# The request returns a json structured string. First we transform the string into a json object:
json_data = json.loads(r.text)

# Next step is to convert the json object to an array, there are many ways to do this. Here is one 
# example that iterates over the data and converts it into float numbers (the price) and datetime objects 
# (the timestamps) while appending it to an initally empty array.

# Create an empty Numpy array
arr = np.empty((0,2), int)

# Populate the Numpy array, while converting Unix timestamps to datetime objects, and price to float numbers
for l in json_data['data']['tokenDayDatas']:
    arr = np.append(arr, np.array([[datetime.fromtimestamp(l['date']), np.float(l['priceUSD'])]]), axis=0)
    

# Now you have the data in a Numpy array, and you can basically do anything with it. Explore with Numpy and SciPy, or SciKitLearn for machine learning.

# step 4 - plot the data
f, ax = plt.subplots(1,1,figsize=(12,8))
ax.plot((arr[:,0]),arr[:,1], label='USD/ETH' )
ax.legend()
ax.set_xlabel('days')
ax.set_ylabel('usd')
#ax.set_yscale('log')
f.show()
import pdb; pdb.set_trace()

