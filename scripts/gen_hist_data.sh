#!/bin/bash
set -e
# Set env vars
export WEB3_INFURA_PROJECT_ID="${WEB3_INFURA_PROJECT_ID:-9aa3d95b3bc440fa88ea12eaa4456161}"
export DFTOOL_KEY="${DFTOOL_KEY:-19ff97f5f910341bc0c7db98c663394c3f2a83050353e43f0fa9acc70a3212c5}"
export SECRET_SEED="${SECRET_SEED:-25362634}"
export ADDRESS_FILE=$(dirname $(dirname $(readlink -f "$0")))/.github/workflows/data/address.json
export SAMPLES="${SAMPLES:-200}"
# First argument is round number, second is output directory
if [ $# -ne 2 ]; then
    echo "Usage: $0 <round number> <output directory>"
    exit 1
fi

# Get df week
df_week=$1
df_week_original=$df_week
if [ $df_week -lt 5 ]; then
    echo "df_week must be >= 5"
    exit 1
fi

df_week=$(($df_week - 5))

# Get start and end date
date=$(date -d "2022-09-29 +$df_week weeks" +%Y-%m-%d)
now=$(date -d "$date +1 week" +%Y-%m-%d)

CSV_DIR="$2/$df_week_original"
mkdir -p $CSV_DIR


# check if dftool is in path
if ! command -v dftool &> /dev/null
then
    echo "dftool could not be found"
    echo "Try running export PATH=\$PATH:. in the root directory of the repo"
    exit
fi


# Get data
dftool getrate OCEAN $date $now $CSV_DIR
dftool getrate ETH $date $now $CSV_DIR
dftool getrate BNB $date $now $CSV_DIR
dftool getrate EWT $date $now $CSV_DIR
dftool getrate MOVR $date $now $CSV_DIR
dftool getrate MATIC $date $now $CSV_DIR
dftool getrate USDC $date $now $CSV_DIR

if [ $USE_TESTNET -eq 1 ]; then
    dftool query $date $now $SAMPLES $CSV_DIR 5
    dftool query $date $now $SAMPLES $CSV_DIR 80001
    dftool vebals $date $now $SAMPLES $CSV_DIR 5
    dftool allocations $date $now $SAMPLES $CSV_DIR 5
    dftool nftinfo $CSV_DIR 5 $now
    dftool nftinfo $CSV_DIR 80001 $now
else
    dftool query $date $now $SAMPLES $CSV_DIR 1
    dftool query $date $now $SAMPLES $CSV_DIR 56
    dftool query $date $now $SAMPLES $CSV_DIR 137
    dftool query $date $now $SAMPLES $CSV_DIR 246
    dftool query $date $now $SAMPLES $CSV_DIR 1285
    dftool vebals $date $now $SAMPLES $CSV_DIR 1
    dftool allocations $date $now $SAMPLES $CSV_DIR 1
    dftool nftinfo $CSV_DIR 1 $now
    dftool nftinfo $CSV_DIR 56 $now
    dftool nftinfo $CSV_DIR 137 $now
    dftool nftinfo $CSV_DIR 246 $now
    dftool nftinfo $CSV_DIR 1285 $now
fi






cp $CSV_DIR/rate-OCEAN.csv $CSV_DIR/rate-MOCEAN.csv
sed -i -e 's/MOCEAN/OCEAN/g' $CSV_DIR/rate-MOCEAN.csv

reward_amount=25000
if [ $df_week_original -lt 9 ]; then
    reward_amount=5000
fi

dftool calc $CSV_DIR $reward_amount OCEAN