#!/bin/bash
set -e


# Get df week
count_start=$(date -d "2022-09-29" +%Y-%m-%d)
now=$(date +%Y-%m-%d)

df_week=$(($(($(($(($(date -d "$now" +%s) - $(date -d "$count_start" +%s))) / 86400)) / 7)) + 4))
echo $df_week

mkdir -p /tmp/csv/$df_week
cp /tmp/csv/*.csv /tmp/csv/$df_week

echo "DFWEEK=$df_week" >> $GITHUB_ENV