import brownie

BROWNIE_PROJECT = brownie.project.load("./", name="MyProject")

brownie.network.connect("development") #development = ganache


GOD_ACCOUNT = brownie.network.accounts[9]

OPF_ACCOUNT = brownie.network.accounts[8]
OPF_ADDRESS = OPF_ACCOUNT.address

ZERO_ADDRESS = "0x0000000000000000000000000000000000000000"
