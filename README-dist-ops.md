# Rewards Distribution Ops

**Rewards to distribute:**
1. [Passive Rewards](#1-passive-rewards)
2. [Active Rewards](#2-active-rewards)

**Notes**

These instructions are somewhat obsolete, as:
- passive rewards are fully automated & decentralized, via on-chain
- active rewards are fully automated, via github actions

We keep these instructions for reference (for now).

## 1. Passive Rewards

Test local, then run on remote.

### 1.1 Passive Rewards: Local

Test locally using barge as follows.
- First, launch barge
- Then test the flow given in "remote"

### 1.2 Passive Rewards: Remote

Run on remote networks: Rinkeby, Mainnet, etc. Operations are on the deployed `FeeDistributor.vy`. Only admin call call it.
- First, send the rewards to the fee distributor contract
- Then, call distributor's `checkpoint_token()`
- Then, call distributor's `checkpoint_total_supply()`


## 2. Active Rewards

Steps:
- 2.1. Set envvars
- 2.2. Run getrate, volsym, calc
- 2.3. Run dispense

### 2.1 Set envvars

First, make sure you have gone through the steps to install df-py given in the main README. 

Then, be in the df-py directory with proper env't:
```console
cd df-py
source venv/bin/activate
export PATH=$PATH:.
```

Then, find your own `WEB3_INFURA_PROJECT_ID`. Then in console:
```console
export WEB3_INFURA_PROJECT_ID=FILLME #infura
```

Next, get `SECRET_SEED`. This can be anything you want. For DF core team, [use this](https://github.com/oceanprotocol/df-private/blob/main/README.md#secret_seed). Then in console:
```console
export SECRET_SEED=FILLME
```

In console, run the following: (can copy & paste):
```console
export ADDRESS_FILE=~/.ocean/ocean-contracts/artifacts/address.json #v4 and OCEAN addresses

export dfrewards_addr=0x0cea7DA063EA910D6904299b5A29A8b68DBC1947  #DFRewards.sol deployment is same per chain:)

export OCEAN_137_addr=0x282d8efce846a88b159800bd4130ad77443fa1a1  #polygon
export OCEAN_246_addr=0x593122aae80a6fc3183b2ac0c4ab3336debee528  #energyweb
export OCEAN_1_addr=0x967da4048cD07aB37855c090aAF366e4ce1b9F48    #mainnet
export OCEAN_56_addr=0xdce07662ca8ebc241316a15b611c89711414dd1a   #bsc
export OCEAN_1285_addr=0x99C409E5f62E4bd2AC142f17caFb6810B8F0BAAE #moonriver
```

### 2.2 Run getrate, volsym, calc

In console, run the following: (can copy & paste):
```console
export date=`date -d "last Thursday" '+%Y-%m-%d'`

export now=`date '+%Y-%m-%d'`
#if DF4, counting ended early, so instead use: `export now=2022-07-12`

# sample size
export SAMPLE_SIZE=50

# csv directory path
export CSV_PATH="./mydata"

# get rate of tokens data's priced in
dftool getrate OCEAN $date $now $CSV_PATH #output rate-OCEAN.csv
dftool getrate H2O $date $now $CSV_PATH

# get rate of native tokens
dftool getrate ETH $date $now $CSV_PATH
dftool getrate MATIC $date $now $CSV_PATH
dftool getrate BNB $date $now $CSV_PATH
dftool getrate EWT $date $now $CSV_PATH 
dftool getrate MOVR $date $now $CSV_PATH

# query chain, output nftvols & symbols
dftool volsym $date $now $SAMPLE_SIZE $CSV_PATH 137
dftool volsym $date $now $SAMPLE_SIZE $CSV_PATH 246
dftool volsym $date $now $SAMPLE_SIZE $CSV_PATH 1
dftool volsym $date $now $SAMPLE_SIZE $CSV_PATH 56
dftool volsym $date $now $SAMPLE_SIZE $CSV_PATH 1285

# query chain, output % allocations
dftool allocations $date $now $SAMPLE_SIZE $CSV_PATH 1

# query chain, output ve balances
dftool vebals $date $now $SAMPLE_SIZE $CSV_PATH 1

# bring it all together to calculate rewards per lp
dftool calc $CSV_PATH 10000 OCEAN
```

### 2.3 Run dispense

Get a working account. We call it dftool_acct. Either use a previous one, or create a new one. For the latter::
```console
dftool newacct
```

Write down dftool_acct private key & address. And, in console:
```console
export DFTOOL_KEY=FILLME #private key used by dftool dispense
```

Then, inspect `rewardsperlp-OCEAN.csv` to see how much OCEAN each network needs. Write it down.

Then, from DF Treasury multisig, send OCEAN & gas funds sent to the local account for each network. How:
1. In Metamask add-on, add new private key for dftool_acct
2. Go to Mainnet Gnosis Safe [DF Treasury multisig](https://gnosis-safe.io/app/eth:0xad0A852F968e19cbCB350AB9426276685651ce41/home). Ensure it has enough OCEAN. [Wallet info](https://github.com/oceanprotocol/atlantic/blob/master/logs/wallets.md#mainnet-gnosis-safe-df-treasury) 0xad0A852F968e19cbCB350AB9426276685651ce41
3. From mainnet_1:multisig, (a) send 10K OCEAN to dftool_acct, (b) send ETH for gas to new_account
4. From mainnet_1:new_account, (a) _bridge_ OCEAN rewards to polygon_137:dftool_acct, (b) if needed, _bridge_ MATIC to polygon:dftool_acct
5. From mainnet_1:new_account, (a) _bridge_ OCEAN rewards to energyweb_246:dftool_acct, (b) if needed, _bridge_ EWT to energyweb_246:dftool_acct
6. (repeat for other networks as needed)

Finally, the big step: dispense funds. In console:
```console
dftool dispense_active $CSV_PATH 137 $dfrewards_addr $OCEAN_137_addr #polygon
```

Then, confirm:
1. Randomly pick a row in rewardsperlp-OCEAN.csv. Note the address to, and the amount
2. Go to the chain's block explorer -> DFrewards.sol contract -> read -> claimable. E.g. [here](https://polygonscan.com/address/0x0cea7DA063EA910D6904299b5A29A8b68DBC1947#readContract) for Polygon
3. Enter "to (address)" = from the csv
4. Enter "tokenAddress" = OCEAN address for the network. E.g. 0x282d8efce846a88b159800bd4130ad77443fa1a1 for Polygon
5. Click "query". Review the result. It should have the same amount as the csv from step (1). If not, problems :(

Now, dispense funds for remaining chains. In console:
```console
dftool dispense_active $CSV_PATH 1 $dfrewards_addr $OCEAN_1_addr #mainnet
```

We're now done dispensing!

