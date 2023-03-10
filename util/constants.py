import brownie

ZERO_ADDRESS = "0x0000000000000000000000000000000000000000"

AQUARIUS_BASE_URL = "https://v4.aquarius.oceanprotocol.com"
BROWNIE_PROJECT = brownie.project.load("./", name="MyProject")

MAX_ALLOCATE = 10000.0
ACTIVE_REWARDS_MULTIPLIER = 0.5

DO_PUBREWARDS = True

# used by _rankBasedAllocate() as part of reward function
DO_RANK = True
RANK_SCALE_OP = "LOG"  # can be: LIN, POW2, POW4, LOG, SQRT
MAX_N_RANK_ASSETS = 100  # only reward top N assets. Eg 20, 50, 100, 500

# multisig
MULTISIG_ADDRS = {
    1: "0xad0A852F968e19cbCB350AB9426276685651ce41",
    5: "0xd701c6F346a6D99c44cc07E9E9E681B67184BF34",
}

# filled in by oceanutil.py
CONTRACTS: dict = {}  # [chainID][contract_label] : contract_object
