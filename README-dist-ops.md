# Rewards Distribution Ops

### High-level steps

1. query - run per CHAINID (8996, 1, 137, ..)
2. getrate - run per basetoken (OCEAN, H2O)
3. calc - run per rewardtoken (store amt per CHAINID): OCEAN (1+137), EWT (246)..
4. dispense - run per rewardtoken * CHAINID: OCEAN * 1, OCEAN * 137, EWT * 246..

### Specific steps

First, find your own WEB3_INFURA_PROJECT_ID. Then in console:
```console
export WEB3_INFURA_PROJECT_ID=((FILL THIS IN)) #infura
```

In console, run the following: (can copy & paste):
```console
export ADDRESS_FILE=~/.ocean/ocean-contracts/artifacts/address.json #v4 and OCEAN addresses

export date=`date -d "last Thursday" '+%Y-%m-%d'`
export now=`date '+%Y-%m-%d'`

export dfrewards_addr=0x0cea7DA063EA910D6904299b5A29A8b68DBC1947

export OCEAN_137_addr=0x282d8efce846a88b159800bd4130ad77443fa1a1  polygon
export OCEAN_246_addr=0x593122aae80a6fc3183b2ac0c4ab3336debee528  #energyweb
export OCEAN_1_addr=0x967da4048cD07aB37855c090aAF366e4ce1b9F48    #mainnet
export OCEAN_56_addr=0xdce07662ca8ebc241316a15b611c89711414dd1a   #bsc
export OCEAN_1285_addr=0x99C409E5f62E4bd2AC142f17caFb6810B8F0BAAE #moonriver

dftool query $date $now 50 mydata 137
dftool query $date $now 50 mydata 246
dftool query $date $now 50 mydata 1
dftool query $date $now 50 mydata 56
dftool query $date $now 50 mydata 1285

dftool getrate OCEAN $date $now mydata
dftool getrate H2O $date $now mydata

dftool calc mydata 10000 OCEAN
```

Then, open file approved-137.csv, and change `OCEAN` -> `MOCEAN` (Polygon workaround)

Now, we'll line up a local account. First, in console:
```
dftool newacct #create account
```

Write down its private key & address. And use its hint to set envvar:
```console
export DFTOOL_KEY=((FILL THIS IN)) #private key used by dftool dispense
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

### Appendix: More chain info

From docs: https://docs.oceanprotocol.com/concepts/networks/

| chainid | chain name | OCEAN symbol | OCEAN address |
| ------- | ---------- | ------------ | ------------- |
| 137     | polygon    | MOCEAN       | 0x282d8efce846a88b159800bd4130ad77443fa1a1 |
| 246     | energyweb  | OCEAN        | 0x593122aae80a6fc3183b2ac0c4ab3336debee528 |
| 1       | mainnet    | OCEAN        | 0x967da4048cD07aB37855c090aAF366e4ce1b9F48 |
| 56      | bsc        | OCEAN        | 0xdce07662ca8ebc241316a15b611c89711414dd1a  |
| 1285    | moonriver  | OCEAN        | 0x99C409E5f62E4bd2AC142f17caFb6810B8F0BAAE |
