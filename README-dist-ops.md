# Rewards Distribution Ops

Outline:
- Step 0: Set envvars
- Step 1, 2, 3: Run query, getrate, calc
- Step 4: Run dispense

### Step 0: Set envvars

First, find your own `WEB3_INFURA_PROJECT_ID`. Then in console:
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

### Step 1, 2, 3: Run query, getrate, calc

In console, run the following: (can copy & paste):
```console
export date=`date -d "last Thursday" '+%Y-%m-%d'`
export now=`date '+%Y-%m-%d'`

dftool query $date $now 50 mydata 137 #output approved-137.csv, poolvols-137.csv, stakes-chain137.csv
dftool query $date $now 50 mydata 246
dftool query $date $now 50 mydata 1
dftool query $date $now 50 mydata 56
dftool query $date $now 50 mydata 1285

dftool getrate OCEAN $date $now mydata #output rate-OCEAN.csv
dftool getrate H2O $date $now mydata
```

Then, open file `approved-137.csv`, and change `OCEAN` -> `MOCEAN` (Polygon workaround)

Then, in console:
```console
dftool calc mydata 10000 OCEAN # output rewardsperlp-OCEAN.csv
```


### Step 4: Run dispense

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
dftool dispense mydata 137 $dfrewards_addr $OCEAN_137_addr #polygon
```

Then, confirm:
1. Randomly pick a row in rewardsperlp-OCEAN.csv. Note the address to, and the amount
2. Go to the chain's block explorer -> DFrewards.sol contract -> read -> claimable. E.g. [here](https://polygonscan.com/address/0x0cea7DA063EA910D6904299b5A29A8b68DBC1947#readContract) for Polygon
3. Enter "to (address)" = from the csv
4. Enter "tokenAddress" = OCEAN address for the network. E.g. 0x282d8efce846a88b159800bd4130ad77443fa1a1 for Polygon
5. Click "query". Review the result. It should have the same amount as the csv from step (1). If not, problems :(

Now, dispense funds for remaining chains. In console:
```console
dftool dispense mydata 246 $dfrewards_addr $OCEAN_246_addr #energyweb
#then, confirm

dftool dispense mydata 1 $dfrewards_addr $OCEAN_1_addr #mainnet
#then, confirm

dftool dispense mydata 56 $dfrewards_addr $OCEAN_56_addr #bsc
#then, confirm

dftool dispense mydata 1285 $dfrewards_addr $OCEAN_1285_addr #moonriver
#then, confirm
```

We're now done!!
