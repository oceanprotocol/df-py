FROM python:3.8
USER root
WORKDIR /app/df-py
COPY requirements.txt requirements.txt
RUN pip3 install -r requirements.txt
RUN brownie pm install OpenZeppelin/openzeppelin-contracts@4.2.0
RUN brownie pm install GNSPS/solidity-bytes-utils@0.8.0

COPY . .
RUN rm -rf build
RUN brownie compile

ENV PATH="/app/df-py:${PATH}"

CMD [ "tail","-f","/dev/null" ]