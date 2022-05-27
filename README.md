# DF-PY

<div align="center">
<img src="https://github.com/oceanprotocol/df-py/actions/workflows/black.yml/badge.svg"/>
<img src="https://github.com/oceanprotocol/df-py/actions/workflows/mypy.yml/badge.svg"/>
<img src="https://github.com/oceanprotocol/df-py/actions/workflows/pylint.yml/badge.svg"/>
<img src="https://github.com/oceanprotocol/df-py/actions/workflows/test.yml/badge.svg"/>
</div>
<br/>


CLI-based tool to administer Data Farming.


```text
Usage: dftool query|calc|dispense|..

  dftool query - query chain for stakes & volumes
  dftool calc - calculate rewards
  dftool dispense - dispense funds
  ...
```

# Installation

### Prerequisites

Ensure prerequisites:
- Linux/MacOS
- Python 3.8.5+
- solc 0.8.0+ [[Instructions](https://docs.soliditylang.org/en/v0.8.9/installing-solidity.html)]
- Any Ocean Barge pre-requisites. See [here](https://github.com/oceanprotocol/barge) 
- nvm 16.13.2, _not_ nvm 17. To install: `nvm install 16.13.2; nvm use 16.13.2`. [[Details](https://github.com/tokenspice/tokenspice/issues/165)]

#### Install & Run Barge

We use [Ocean Barge](https://github.com/oceanprotocol/barge) to run ganache, deploy contracts to Ganache, and run TheGraph with Ocean subgraphs. The deployed contracts come from github.com/oceanprotocol/contracts. df-py has a local redundant copy in its directory so that brownie easily knows what objects look like.

Let's get Barge going. Open a new terminal and:

```console
#get repo
git clone git@github.com:oceanprotocol/barge.git
cd barge

#ensure v4 repo
git checkout v4

#clean up old containers (to be sure)
docker system prune -a --volumes

#run barge
#-deploys ocean contracts with addresses at ~/.ocean/ocean-contracts/artifacts/address.json
#-sends stdout & stderr to out.txt
./start_ocean.sh --no-aquarius --no-elasticsearch --no-provider --no-dashboard --with-thegraph > out.txt 2>&1 &

#monitor output
tail -f out.txt
```

### Install df-py

Then, open a new terminal and:

```console
#clone repo
git clone https://github.com/oceanprotocol/df-py.git
cd df-py

#create a virtual environment
python -m venv venv

#activate env
source venv/bin/activate

#install dependencies
pip install wheel
pip install -r requirements.txt

#install openzeppelin library, to import from .sol (ignore FileExistsErrors)
brownie pm install OpenZeppelin/openzeppelin-contracts@4.2.0
brownie pm install GNSPS/solidity-bytes-utils@0.8.0

#add pwd to bash path
export PATH=$PATH:.

#compile contracts
dftool compile
```


# Main Usage: CLI

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

# Usage: Running Tests

In terminal:
```console
#run tests for one method, with print statements to console. "-s" is to show output
brownie test util/test/test_calcrewards.py::test_calcRewards1_onechain -s

#run tests for one module
brownie test util/test/test_calcrewards.py

#run all tests. Note: util is the only directory _with_ tests
brownie test util

#run static type-checking. By default, uses config mypy.ini. Note: pytest does dynamic type-checking.
mypy ./

#run linting on code style. Uses .pylintrc
pylint *

#auto-fix some pylint complaints
black ./
```

Brownie uses `pytest` plus [Brownie-specific goodies](https://eth-brownie.readthedocs.io/en/stable/tests-pytest-intro.html).

# Usage: Via Docker

Build the docker image.
```shell
docker build . -t dfpy
```

Usage:
`./dfpy_docker args`

Docker will mount `/tmp/dfpy:/app/data`
Example usage with docker:

```shell
./dfpy_docker help  # prints help 
```

```shell
$ ./dfpy_docker getrate OCEAN 2022-01-01 2022-01-02 /app/data

Arguments: ST=2022-01-01, FIN=2022-01-02, CSV_DIR=/app/data
rate = $0.8774 / OCEAN
Created /app/data/rate-OCEAN.csv
```

# Usage: Brownie Console

From terminal:
```console
brownie console
```

In brownie console:
```python
>>> t = Simpletoken.deploy("TEST", "Test Token", 18, 100, {'from': accounts[0]})
Transaction sent: 0x3f113379b70d00041068b27733c37c2977354d8c70cb0b30b0af3087fca9c2b8
  Gas price: 0.0 gwei   Gas limit: 6721975   Nonce: 0
  Simpletoken.constructor confirmed   Block: 1   Gas used: 551616 (8.21%)
  Simpletoken deployed at: 0x3194cBDC3dbcd3E11a07892e7bA5c3394048Cc87

>>> t.symbol()                                                                                                                                                                                              
'TEST'
```
