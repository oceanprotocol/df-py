# Scheduled Operations

This document describes the scheduled operations that are run on the server and Github Actions.

These operations are run on a regular basis to:
- Keep the df-sql up to date.
- Calculate weekly rewards.
- Checkpoint `FeeDistributor` smart contract.

## DF-SQL
The server runs a cron job that calculates the allocations, vebalances, volumes, and other data. This data is then used to update the df-sql database. The cron job is run every 10 minutes.

## Weekly Rewards
Every Thursday at 12:00 UTC, Github Actions calculates the weekly rewards for the previous week. The results are then uploaded as an artifact to the Github Actions.

## Contract Checkpoint
Every Thursday at 12:00 UTC, Github Actions checkpoints the `FeeDistributor` smart contract. This ensures that the `FeeEstimate` smart contract serves the correct data.