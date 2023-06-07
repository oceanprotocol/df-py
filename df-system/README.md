# Crontab and Shell Scripts

## Overview

Here are the cronjobs and scripts that are used to keep df-sql up to date. These scripts are executed at defined intervals. The scripts carry out tasks such as calculating reward amounts for the current round, fetching NFT information, and updating cloud data.

Below, is the outline of the purpose and workings of each cron job and script.

## Crontab Entries

Three scripts are scheduled to run using cron, a utility that allows tasks to be automatically run in the background at regular intervals.

1. **all.sh**: Runs every 10 minutes.
2. **nftinfo.sh**: Runs every 15 minutes.
3. **updatecloud.sh**: Runs every 15 minutes on Thursdays only.

```bash
*/10 * * * * /app/crons/all.sh
*/15 * * * * /app/crons/nftinfo.sh
*/15 * * * 4 /app/crons/updatecloud.sh
```

## Directories

- df-py is located at `/app/df-py`
- CSVs are located at `~/.dfcsv`
- Historical CSV data is located at `~/.dfcsv/historical/${round_number}`

df-sql is set to scan and sync `~/.dfcsv` folder.

## Cron/Shell Scripts

### all.sh

The all.sh script is used to run the full df-py flow and calculate rewards amounts for the current week.

- Calculates the current date and the date of the previous Thursday. If the current day is Thursday, it sets the 'date' variable to the current date.
- Retrieves rate data for a selection of cryptocurrencies, spanning the date range from the previously defined 'date' to 'now'
- Fetches volumes, symbols, allocations and veOCEAN balances by calling the `dftool volsym`, `vebals`, and `allocations` commands.
- Calculates the active and passive rewards.
- Moves all CSV files generated during the process from /tmp/dfpy directory to the ~/.dfcsv dicretory.

### nftinfo.sh

This script retrieves NFT information and moves the corresponding CSV files. It works in the following steps:

- NFT Info Retrieval: For each of the specified chain ID (1, 137), it retrieves information of all NFTs on that chain by running the `dftool nftinfo` command.
- Move CSV Files: It then moves the generated CSV files containing NFT info from the /tmp/dfpy/ directory to the ~/.dfcsv/ directory.

### updatecloud.sh

This script syncs local historical data files with the Google Cloud Storage.

- Changes directory to the historical data folder.
- Counts the number of files before synchronization.
- Synchronizes local files with Google Cloud Storage bucket.
- Counts the number of files after synchronization.
- If new files are added during sync, identifies the new file, and if it's a directory, performs additional actions including copying nftinfo csvs, calculating weeks, and running a helper script which calculates the passive rewards for that round.
- Syncs back to Google Cloud Storage bucket to ensure it has the most up-to-date data.

## Helper Scripts

These scripts are not directly called by cron jobs; instead, they are executed as part of the above scripts, which are themselves triggered by the cron jobs.

### dfpy_docker

Executes commands inside a Docker container using the image `dfpy`.

Called by: [`all.sh`](#allsh), [`nftinfo.sh`](#nftinfosh)

- Loads environment variables from an .env file located in the df-py directory.
- Mounts two volumes into the container, one for CSV output and one for the address file.
  - The output directory for the data is located at `/tmp/dfpy` on the local machine.
  - The script assumes that the address file is located at `/app/df-py/.github/workflows/data/address.json`
- Passes additional arguments to the Docker command.

### dfpy_docker_past

Functions similarly to the [dfpy_docker](#dfpy_docker) script with a key difference: it mounts the /root/.dfcsv/historical folder as the data directory, which allows the script to utilize existing CSV files.

Called by: [`helperscript.sh`](#helperscriptsh)

### helperscript.sh

Performs calculations based on historical data for a specific round. The sole argument it takes is the round number, which is used to determine the time period for the calculations. The script utilizes [dfpy_docker_past](#dfpy_docker_past) script to utilize existing csvs in the history dir, the script then calculates real time veOCEAN balances and passive rewards. The csvs are stored in historical data directory under a subdirectory named after the round number.

Called by: [`updatecloud.sh`](#updatecloudsh)
