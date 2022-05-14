import brownie

ZERO_ADDRESS = "0x0000000000000000000000000000000000000000"

BARGE_ADDRESS_FILE = '~/.ocean/ocean-contracts/artifacts/address.json'

BROWNIE_PROJECT = brownie.project.load("./", name="MyProject")
