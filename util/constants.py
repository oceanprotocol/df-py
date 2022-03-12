import brownie

BROWNIE_PROJECT = brownie.project.load("./", name="MyProject")

brownie.network.connect("development") #development = ganache

GOD_ACCOUNT = brownie.network.accounts[0]

ZERO_ADDRESS = "0x0000000000000000000000000000000000000000"
