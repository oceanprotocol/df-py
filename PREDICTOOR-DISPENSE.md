# Predictoor Rewards Dispense

This document describes the process for dispensing Predictoor rewards.

## Process Overview

Predictoor rewards are dispensed weekly via a GitHub Action workflow.

- **Workflow:** [.github/workflows/dispense-predictoor-usdc.yaml](.github/workflows/dispense-predictoor-usdc.yaml)
- **Schedule:** Every Monday at 00:00 UTC.
- **Manual Trigger:** Can be triggered manually via `workflow_dispatch` with a custom amount of tokens.

## How it works

The workflow performs the following steps:

1. **Setup:** Installs dependencies and configures environment variables (RPC URLs, private keys).
2. **Data Retrieval:** Runs `dftool predictoor_data` to fetch predictoor performance data for the previous week.
3. **Reward Calculation:** Runs `dftool calc predictoor_rose` to calculate rewards based on the fetched data.
4. **Dispense:** Runs `dftool dispense_active` to send rewards to the `DFRewards` contract on Sapphire.
5. **Upload:** Renames the results folder and uploads the CSV files to Google Cloud Storage for historical tracking.

## Networks and Tokens

- **Chain:** Sapphire Mainnet (Chain ID 23294)
- **Token:** USDC (configured via `--TOKEN_ADDR` in the dispense step)
- **Reward Contract:** `DFRewards` contract address is specified in the dispense step.

## Manual Execution

Go to the "Actions" tab in GitHub, select "Dispense Predictoor USDC Rewards", and click "Run workflow". You can specify the `amt_of_tokens` to distribute.
