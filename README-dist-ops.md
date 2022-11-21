# Rewards Distribution Ops

- [Active Rewards](#active-rewards)
- [Passive Rewards](#passive-rewards)

## Active Rewards

Outline:
- Step 0: Set envvars
- Step 1, 2, 3: Run getrate, query, calc
- Step 4: Run dispense
- Step 5, 6: Publish csvs, blog post, tweet

### Step 0: Set envvars

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

### Step 1, 2, 3: Run getrate, query, calc

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
dftool query $date $now $SAMPLE_SIZE $CSV_PATH 137
dftool query $date $now $SAMPLE_SIZE $CSV_PATH 246
dftool query $date $now $SAMPLE_SIZE $CSV_PATH 1
dftool query $date $now $SAMPLE_SIZE $CSV_PATH 56
dftool query $date $now $SAMPLE_SIZE $CSV_PATH 1285

# query chain, output % allocations
dftool allocations $date $now $SAMPLE_SIZE $CSV_PATH 1

# query chain, output ve balances
dftool vebals $date $now $SAMPLE_SIZE $CSV_PATH 1

# bring it all together to calculate rewards per lp
dftool calc $CSV_PATH 10000 OCEAN
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
dftool dispense $CSV_PATH 137 $dfrewards_addr $OCEAN_137_addr #polygon
```

Then, confirm:
1. Randomly pick a row in rewardsperlp-OCEAN.csv. Note the address to, and the amount
2. Go to the chain's block explorer -> DFrewards.sol contract -> read -> claimable. E.g. [here](https://polygonscan.com/address/0x0cea7DA063EA910D6904299b5A29A8b68DBC1947#readContract) for Polygon
3. Enter "to (address)" = from the csv
4. Enter "tokenAddress" = OCEAN address for the network. E.g. 0x282d8efce846a88b159800bd4130ad77443fa1a1 for Polygon
5. Click "query". Review the result. It should have the same amount as the csv from step (1). If not, problems :(

Now, dispense funds for remaining chains. In console:
```console
dftool dispense $CSV_PATH 1 $dfrewards_addr $OCEAN_1_addr #mainnet
```

We're now done dispensing!

Next steps are to get the word out.

### Step 5: Publish csvs into Ocean Market

First, create a tarball of the data. In console:
```console
cd $CSV_PATH
tar -cvf df3-final.tar *.csv
gzip df3-final.tar
# result is df3-final.tar.gz
```

Then, make the data available in GDrive, as follows:
- Go to [this higher-level Gfolder]([https://drive.google.com/drive/folders/1yFj08QgNTuFPjxzzPRLBYVyaCmmqghJz](https://drive.google.com/drive/folders/12jvYl7c2kcHIVrbosFBCgoCYCWkE-Zkn))
- within that sub-folder, right-click, "upload file", select the tarball, click ok
- right-click the uploaded file, and change permissions so that anyone with link can view

Now, publish into Ocean Market
- Open your browser. 
- Go to [https://market.oceanprotocol.com/](https://market.oceanprotocol.com/publish/1)
- Connect wallet
- From your wallet, select any chain. Ensure you have tokens for gas. Eth mainnet is approx $20, the rest are a few cents max.
- Fill out info, based on previous examples, adapting to your DFx. Prev: [DF1](https://market-git-fix-1562-oceanprotocol.vercel.app/asset/did:op:dc1d8c161b641011614e4de03f5023bbba55fefcc91cc88d8074656ca91bf483), [DF2](https://market-git-fix-1562-oceanprotocol.vercel.app/asset/did:op:a3aa14de333ee1ecb3b8a842954033c1c0004f9e77020cacb861843478c1079c)

### Step 6: Write blog post, tweet

Write & publish blog post:
- Go to medium.com, log in. If you're not yet an Editor in Ocean Protocol blog, ask Marcom to add you.
- From medium, click on new story. 
- Fill out info in new story, based on previous examples, adapting to your DFx. Prev: [DF1/2](https://medium.com/oceanprotocol/data-farming-df1-completed-df2-started-7a660ee84afe), [DF2/3](https://medium.com/oceanprotocol/data-farming-df2-completed-df3-started-cfedc32fa3c9), [DF3/4](https://blog.oceanprotocol.com/data-farming-df3-completed-df4-started-dc8958db5886), [DF4/5](https://blog.oceanprotocol.com/data-farming-df4-completed-8346b4c1cf06)
- Be sure to add stats to the story: use GDrive csvs
- Be sure to link to the new data asset that you just published in Ocean Market
- Be sure to update the image. Create the image from [these GSlides](https://docs.google.com/presentation/d/1auR_fm19RvpkkiNEMDYU7hR_qU7To1kI3tDBzxe92bk/edit?usp=sharing) in [this Gfolder](https://drive.google.com/drive/folders/1Lz2qODAJUySIIKaMIysp-dVCThgLTUwx)
- Be sure to set tags: Homepage, Data Farming, Artificial Intelligence, Defi, Data
- Publish!

Update link in DF Series post:
- Go to [the post](https://blog.oceanprotocol.com/ocean-data-farming-series-c7922f1d0e45)
- Add the link to the article just published

Write & publish tweet
- Ideally tweet from [@OceanDAO_](https://twitter.com/OceanDAO_) account, otherwise from personal
- Write tweet content. Examples: [DF2/3](https://twitter.com/trentmc0/status/1542595137511063555), [DF3/4](https://twitter.com/trentmc0/status/1545153163627577344), [DF4/5](https://twitter.com/trentmc0/status/1547675474649763840)
- Publish!

Share to Marcom, and broader Ocean team
- Goto slack, #general channel, copy the tweet link in, hit send
- Then forward (share) that slack msg to #marcom_x_nile channel, and tag marcom folks. If you don't have access to that channel, ask for it.
- FYI Marcom will likely RT from @oceanprotocol and elsewhere

Share to community:
- Share link to tweet in [TG Ocean official](https://t.me/oceanprotocol_community)
- Share link to tweet in [TG DataFarm](https://t.me/Farm_Ocean)
- Elsewhere?

## Passive Rewards
Note, only the admin can call FeeDistributor.vy so to test/verify this is working in local network, please use barge.

#### Local Testnet - Use Barge
Launch barge
Test the flow

#### Rinkeby, Mainnet and otherwise
Only admin can call FeeDistributor.vy

Send the rewards to the fee distributor contract, then call the following functions:
- `fee_distributor.checkpoint_token()`
- `fee_distributor.checkpoint_total_supply()`
