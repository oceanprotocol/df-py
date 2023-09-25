FROM python:3.8
USER root

COPY . /app/df-py
WORKDIR /app/df-py

RUN python3.8 -m pip install --upgrade pip
RUN python3.8 -m pip install .

RUN brownie pm install OpenZeppelin/openzeppelin-contracts@4.2.0
RUN brownie pm install GNSPS/solidity-bytes-utils@0.8.0
RUN brownie networks add mumbai mumbai host=https://polygon-mumbai.infura.io/v3/${WEB3_INFURA_PROJECT_ID} chainid=80001 explorer=https://api.etherscan.io/api provider=infura >/dev/null
RUN brownie networks add sapphire sapphire host=https://sapphire.oasis.io chainid=23294
RUN brownie networks add sapphire-testnet sapphire-testnet host=https://testnet.sapphire.oasis.dev chainid=23295

COPY . .
RUN rm -rf build
RUN brownie compile

ENV PATH="/app/df-py:${PATH}"

ENTRYPOINT [ "python3", "/app/df-py/dftool" ]
