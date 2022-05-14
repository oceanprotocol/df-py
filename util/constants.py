import brownie

ZERO_ADDRESS = "0x0000000000000000000000000000000000000000"

BARGE_ADDRESS_FILE = '~/.ocean/ocean-contracts/artifacts/address.json'

MARKET_ASSET_BASE_URL = "https://v4.market.oceanprotocol.com/asset/"

BROWNIE_PROJECT = brownie.project.load("./", name="MyProject")
