# DF-PY

<div align="center">
<img src="https://github.com/oceanprotocol/df-py/actions/workflows/black.yml/badge.svg"/>
<img src="https://github.com/oceanprotocol/df-py/actions/workflows/mypy.yml/badge.svg"/>
<img src="https://github.com/oceanprotocol/df-py/actions/workflows/pylint.yml/badge.svg"/>
<img src="https://github.com/oceanprotocol/df-py/actions/workflows/test.yml/badge.svg"/>
</div>
<br/>

CLI-based Data Farming (DF) & veOCEAN (VE) backend. It's used for weekly "dispense" ops and to create data for VE/DF frontend.

Usage: in console, type `dftool` to see further commads.

Data flow and csvs: See "Data Flow in dftool" **[GSlides 2&3](https://docs.google.com/presentation/d/15Zys9X5eLzlApqhobdGpn9SdGrFuKyr2W14D4dSSzgk/edit?usp=share_link)**


# Installation

### Prerequisites

Ensure prerequisites:
- Linux/MacOS
- Python 3.8.5+
- mypy, pylint, black. `sudo apt install mypy pylint black`
- solc 0.8.0+ [[Instructions](https://docs.soliditylang.org/en/v0.8.9/installing-solidity.html)]
- Any Ocean Barge pre-requisites. See [here](https://github.com/oceanprotocol/barge)
- nvm 16.13.2, _not_ nvm 17. To install: `nvm install 16.13.2; nvm use 16.13.2`. [[Details](https://github.com/tokenspice/tokenspice/issues/165)]

#### Setup for Local: Install & Run Barge

We use [Ocean Barge](https://github.com/oceanprotocol/barge) to run ganache, deploy contracts to Ganache, and run TheGraph with Ocean subgraphs. The deployed contracts come from github.com/oceanprotocol/contracts. df-py has a local redundant copy in its directory so that the system easily knows what objects look like.

Let's get Barge going. Open a new terminal and:

```console
#get repo
git clone git@github.com:oceanprotocol/barge.git
cd barge

#clean up old containers (to be sure)
docker system prune -a --volumes

#run barge
#-deploys ocean contracts with addresses at ~/.ocean/ocean-contracts/artifacts/address.json
#-only runs the components it needs
export GANACHE_FORK="london"
./start_ocean.sh --no-aquarius --no-elasticsearch --no-provider --no-dashboard --with-thegraph
```

### Install df-py

Then, open a new terminal and:

```console
#clone repo
git clone https://github.com/oceanprotocol/df-py.git
cd df-py

#create & activate virtual env't
python -m venv venv
source venv/bin/activate

#install dependencies
pip install wheel
pip install -r requirements.txt

#install openzeppelin library, to import from .sol
npm install @openzeppelin/contracts

#add pwd to bash path
export PATH=$PATH:.

#set judge private key
#  - get at private repo https://github.com/oceanprotocol/private-keys
#  - CI automatically sees it via Github Actions Secrets
export JUDGE_PRIVATE_KEY=<judge key>
```


# CLI

`dftool` is the main tool. In main terminal:
```console
#top-level help, lists all tools
dftool

#see help for key functions
dftool calc
dftool dispense
...
```

Then, simply follow the usage directions:)

# Running Tests

In terminal:
```console
#run tests for one method, with print statements to console. "-s" is to show output
pytest df_py/volume/test/test_calcrewards.py::test_simple -s

#run tests for one module
pytest df_py/volume/test/test_calcrewards.py

#run all tests. Note: util is the only directory _with_ tests
pytest test df_py/util

#run static type-checking. By default, uses config mypy.ini. Note: pytest does dynamic type-checking.
mypy ./

#run linting on code style. Uses .pylintrc
pylint *

#auto-fix some pylint complaints
black ./
```

# Setup for Remote Networks

Examples so far were on a local chain. Let's do a one-time setup for remote networks. In console:
```console
export POLYGON_RPC_URL=https://polygon-rpc.com/
export MUMBAI_RPC_URL=https://polygon-mumbai.blockpi.network/v1/rpc/public
```

Or using an Infura ID, here is an example for polygon.
Please note that you do not need to include the Infura Id in the URL,
they will be glued together at runtime. However, you need to specify which networks use the infura project id,
by a comma separated value list in the INFURA_NETWORKS env var.
```
export WEB3_INFURA_PROJECT_ID=***
export POLYGON_RPC_URL=https://polygon-mainnet.infura.io/v3/
export INFURA_NETWORKS=polygon,mumbai
```

Now, you can use those networks simply by specifying a different chainid in `dftool` calls.

# Rewards Distribution Ops

Happens via regularly-scheduled Github Actions:

- Passive: [dispense_passive.yml](.github/workflows/dispense_passive.yml)
- Active: [flow.yml](.github/workflows/flow.yml)

More info: [README-crons-ops.md](README-crons-ops.md)

# DFRewards Owner Control Ops

See [README-control-ops.md](README-control-ops.md)

# Docker

Here's how to use df-py running inside a Docker container.

### Install & Use Docker Locally

Build the docker image.
```shell
docker build . -t dfpy
```

Usage:
`./dfpy_docker args`

Docker will mount `/tmp/dfpy:/app/data`
Which will be located inside of `/root/.dfcsv`

Example usage with docker:

```shell
./dfpy_docker help  # prints help
```

```shell
$ ./dfpy_docker get_rate OCEAN 2022-01-01 2022-01-02 /app/data

Arguments: ST=2022-01-01, FIN=2022-01-02, CSV_DIR=/app/data
rate = $0.8774 / OCEAN
Created /app/data/rate-OCEAN.csv
```

### Docker Using Remote Networks

Expand configured networks in the Docker container by editing the `Dockerfile` as follows:
```
...
RUN export POLYGON_URL=https://polygon-rpc.com/
...
COPY . .
RUN rm -rf build
```

### Docker Using Contract Addresses

Here's how to configure docker to access contracts.

First, [address.json on contracts github](https://github.com/oceanprotocol/contracts/blob/v4main/addresses/address.json) to local.

Then, configure `dfpy_docker` like so:
```
docker run --env-file ./.env -v /tmp/dfpy:/app/data -v /app/df-py/address.json:/address.json --rm dfpy $@
```

# End-to-end With SQL and Webapp

Let's have an end-to-end flow of df-py, df-sql, and df-web.

Overall flow:
- [`df-sql`](https://github.com/oceanprotocol/df-sql) runs `df-py/dftool` to generate csvs, and then serve them up in a SQL API.
- Then, [`df-web`](https://github.com/oceanprotocol/df-web) consumes this API

More info:
- [High-level diagram](https://user-images.githubusercontent.com/25263018/202422416-e7c8e196-fd7a-4c51-be01-bffe7296b073.png) (from df-sql repo)
- `df-sql` reads csvs in `~/.dfcsv/`

Here's how to set up this flow.

First, create folders, if they don't yet exist.
```console
mkdir /tmp/dfpy/
mkdir ~/.dfcsv/ # df-sql reads csvs from here
```

Then, create a new script named `getAllRecords-df-sql.sh`, and fill it with the following content.
```text
cd /app/df-py/
date=`date -dlast-wednesday '+%Y-%m-%d'`
now=`date '+%Y-%m-%d'`

/app/df-py/dfpy_docker get_rate OCEAN $date $now /app/data &&
/app/df-py/dfpy_docker query $date latest 1 /app/data 1 &&
/app/df-py/dfpy_docker query $date latest 1 /app/data 137 &&
/app/df-py/dfpy_docker calc /app/data 10000 OCEAN &&
mv /tmp/dfpy/* ~/.dfcsv/
```

Now, add the script to our crontab:
```console
*/10 * * * * /app/df-py/getAllRecords-df-sql.sh
```

You can adjust this by changing this path in both repositories and redeploying.

## Gotchas and workarounds

This section provides tactics if you encounter issues like `KeyError "development"`.

### Gotcha: KeyError "development"

If you run a test and get an error like `KeyError: "development"`

Then your problem is: barge wasn't able to deploy contracts to ganache. Then it couldn't update `~/.ocean/ocean-contracts/artifacts/address.json` with a new sub-dict holding all the addresses at `"development"` chain (ganache). See [#562](https://github.com/oceanprotocol/df-py/issues/562).

How to fix:
- Tactic: in barge console: `./cleanup.sh`
- Tactic: in any console: `rm -rf ~/.ocean`
- More tactics at [barge README](https://github.com/oceanprotocol/barge)


## Release process (developers)
In order to release a new version of df-py, simply create a new GitHub release. As opposed to other Ocean Protocol python repos, there is no need to use bumpversion.
