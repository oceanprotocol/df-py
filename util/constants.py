import brownie

ZERO_ADDRESS = "0x0000000000000000000000000000000000000000"

MARKET_ASSET_BASE_URL = "https://v4.market.oceanprotocol.com/asset/"

BROWNIE_PROJECT = brownie.project.load("./", name="MyProject")

#filled in by oceanutil.py
CONTRACTS: dict = {}  # [chainID][contract_label] : contract_object
