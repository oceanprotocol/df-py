# Rewards Distribution Ops

Contract locations. Deployed to polygon, energyweb, FIXME
```
DFRewards: 0x0cea7DA063EA910D6904299b5A29A8b68DBC1947
DFStrategy: 0x0000000000cEAe464ae8a73EDDc0B482383490e7
```

### OPF steps: high-level
1. query - run per CHAINID (8996, 1, 137, ..)
2. getrate - run per basetoken (OCEAN, H2O)
3. calc - run per rewardtoken (store amt per CHAINID): OCEAN (1+137), EWT (246)..
4. dispense - run per rewardtoken*CHAINID: OCEAN*1, OCEAN*137, EWT*246..

### OPF steps: CLI

```text
1. dftool query ST FIN NSAMP CSV_DIR CHAINID - query chain, get (pools, stakes, vols, approved)
2. dftool getrate TOKEN_SYMBOL ST FIN CSV_DIR - get exchange rate
3. dftool calc CSV_DIR TOT_TOKEN TOKEN_SYMBOL - from (pools, stakes, .., rates), calc rewards
4. dftool dispense CSV_DIR CHAINID [DFREWARDS_ADDR] [TOKEN_ADDR] - from rewards, dispense funds
```

### Env variables

- `WEB3_INFURA_PROJECT_ID` - Infura project id
- `DFTOOL_KEY` - The private key of the address to distribute the rewards
- `ADDRESS_FILE` - path to `address.json` file

### dftool query

Berkay's query script
```console
export date=`date -d "last Thursday" '+%Y-%m-%d'`
export now=`date '+%Y-%m-%d'`

./dftool query $date $now 50 /tmp/dfpy 1 && 
./dftool query $date $now 50 /tmp/dfpy 137 && 
./dftool query $date $now 50 /tmp/dfpy 246 && 
./dftool query $date $now 50 /tmp/dfpy 1285
```

### dftool dispense top-level steps

Steps: ([Ref](https://github.com/oceanprotocol/df-issues/issues/66#issuecomment-1164729816))

1. inspect rewardsperlp-OCEAN.csv to see how much OCEAN each network needs
2. Generate local account via `dftool newacct`. Remember private key & address.
3. For each chain:
   - have OCEAN sent -> local account
   - have gas funds sent -> local account
   - from local account, on CLI: `dftool dispense` (details below)

### dftool dispense parameters

(For step 2.3 above)

```text
dftool dispense CSV_DIR CHAINID [DFREWARDS_ADDR] [TOKEN_ADDR] [BATCH_NBR]

Param values picked:
  CSV_DIR -- arbitrarily set to /tmp/dfpy
  
  CHAINID -- 
    1: mainnet
    56: bsc
    137: polygon
    246: energyweb
    1285: moonriver
    
  DFREWARDS_ADDR -- 0x0cea7DA063EA910D6904299b5A29A8b68DBC1947
  
  TOKEN_ADDR -- address of OCEAN token per network. https://docs.oceanprotocol.com/concepts/networks/
    137: polygon   -- MOCEAN -- 0x282d8efce846a88b159800bd4130ad77443fa1a1
    246: energyweb  -- OCEAN -- 0x593122aae80a6fc3183b2ac0c4ab3336debee528
    1: mainnet      -- OCEAN -- 0x967da4048cD07aB37855c090aAF366e4ce1b9F48
    56: bsc         -- OCEAN -- 0xdce07662ca8ebc241316a15b611c89711414dd1a 
    1285: moonriver -- OCEAN -- 0x99C409E5f62E4bd2AC142f17caFb6810B8F0BAAE
    
  BATCH_NBR -- specify the batch number to run dispense only for that batch. If not given, runs dispense for all batches.
    - we can ignore this param to start, only use if we need

Transactions are signed with envvar 'DFTOOL_KEY`.
```

### dftool dispense: Polygon issue & workaround:

(From Berkay)

We had a problem when dispensing and calculating rewards for polygon, because the symbols didn't match MOCEAN - OCEAN

I changed the MOCEAN to OCEAN in the approved tokens csv file - `dftool calc` worked

For dispensing I added the following line as a temporary fix: [github issue](https://github.com/oceanprotocol/df-py/issues/177)
```python
token_symbol = token_symbol.upper().replace("MOCEAN", "OCEAN")
```
