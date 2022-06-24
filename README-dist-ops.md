# Rewards Distribution Ops

Outline:
- Step 0: Set envvars
- Step 1, 2, 3: Run query, getrate, calc
- Step 4: Run dispense

### Step 0: Set envvars

First, find your own WEB3_INFURA_PROJECT_ID. Then in console:
```console
export WEB3_INFURA_PROJECT_ID=FILLME #infura
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

dftool query $date $now 50 mydata 137
dftool query $date $now 50 mydata 246
dftool query $date $now 50 mydata 1
dftool query $date $now 50 mydata 56
dftool query $date $now 50 mydata 1285

dftool getrate OCEAN $date $now mydata
dftool getrate H2O $date $now mydata

dftool calc mydata 10000 OCEAN
```

Then, open file `approved-137.csv`, and change `OCEAN` -> `MOCEAN` (Polygon workaround)

### Step 4: Run dispense

Create a local account. In console:
```console
dftool newacct
```

Write down its private key & address. And, in console:
```console
export DFTOOL_KEY=FILLME #private key used by dftool dispense
```

Then, inspect `rewardsperlp-OCEAN.csv` to see how much OCEAN each network needs

Then, have the OCEAN & gas funds sent to that local account, for each network. (Eg ask Alex)

Finally, the big step: dispense funds. In console:
```console
dftool dispense mydata 137 $dfrewards_addr $OCEAN_137_addr
#then, confirm

dftool dispense mydata 246 $dfrewards_addr $OCEAN_246_addr
#then, confirm

dftool dispense mydata 246 $dfrewards_addr $OCEAN_1_addr
#then, confirm

dftool dispense mydata 246 $dfrewards_addr $OCEAN_56_addr
#then, confirm

dftool dispense mydata 246 $dfrewards_addr $OCEAN_1285_addr
#then, confirm
```

We're now done!!
