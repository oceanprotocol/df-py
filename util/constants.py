import brownie

BROWNIE_PROJECT = brownie.project.load("./", name="MyProject")

brownie.network.connect("development") #development = ganache
