import brownie

ZERO_ADDRESS = "0x0000000000000000000000000000000000000000"

MARKET_ASSET_BASE_URL = "https://market.oceanprotocol.com/asset/"
AQUARIUS_BASE_URL = "https://v4.aquarius.oceanprotocol.com"

BROWNIE_PROJECT = brownie.project.load("./", name="MyProject")

MAX_ALLOCATE = 10000.0

# filled in by oceanutil.py
CONTRACTS: dict = {}  # [chainID][contract_label] : contract_object
