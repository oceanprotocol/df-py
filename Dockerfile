FROM python:3.8
USER root

COPY . /app/df-py
WORKDIR /app/df-py

RUN python3.8 -m pip install --upgrade pip
RUN python3.8 -m pip install .

RUN apt-get update && apt-get install -y npm
RUN npm install @openzeppelin/contracts
ENV MUMBAI_RPC_URL="https://polygon-mumbai.infura.io/v3/"
ENV OASIS_SAPPHIRE_RPC_URL="https://sapphire.oasis.io"
ENV OASIS_SAPPHIRE_TESTNET_RPC_URL="https://testnet.sapphire.oasis.dev"
ENV INFURA_NETWORKS="mumbai"

COPY . .
RUN rm -rf build

ENV PATH="/app/df-py:${PATH}"

ENTRYPOINT [ "python3", "/app/df-py/dftool" ]
