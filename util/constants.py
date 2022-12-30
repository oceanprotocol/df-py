import brownie

ZERO_ADDRESS = "0x0000000000000000000000000000000000000000"

AQUARIUS_BASE_URL = "https://v4.aquarius.oceanprotocol.com"
BROWNIE_PROJECT = brownie.project.load("./", name="MyProject")

MAX_ALLOCATE = 10000.0


RANK_SCALE_OP = "LIN" # can be: LIN, POW2, POW4, LOG, SQRT

MAX_N_RANK_ASSETS = 50  # only reward top 100 assets in rank-based setup

MULTISIG_ADDRS = {
    1: "0xad0A852F968e19cbCB350AB9426276685651ce41",
    5: "0xd701c6F346a6D99c44cc07E9E9E681B67184BF34",
}

# filled in by oceanutil.py
CONTRACTS: dict = {}  # [chainID][contract_label] : contract_object
