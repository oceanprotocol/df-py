import brownie

ZERO_ADDRESS = "0x0000000000000000000000000000000000000000"

BARGE_ADDRESS_FILE = '~/.ocean/ocean-contracts/artifacts/address.json'
BARGE_SUBGRAPH_URI = 'http://127.0.0.1:9000'

BROWNIE_PROJECT = brownie.project.load("./", name="MyProject")
