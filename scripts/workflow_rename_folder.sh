#!/bin/bash
set -e

# Get df week
count_start=$(date -d "2022-09-29" +%Y-%m-%d)

if [ -z "$1" ]; then
	now=$(date +%Y-%m-%d)
else
	now="$1"
fi

suffix="$2"

df_week=$(($(($(($(($(date -d "$now" +%s) - $(date -d "$count_start" +%s))) / 86400)) / 7)) + 4))
df_foldersuffix="${df_week}${suffix}"
echo $df_foldersuffix

mkdir -p /tmp/csv/$df_foldersuffix
cp /tmp/csv/*.csv /tmp/csv/$df_foldersuffix

echo "DFWEEK=$df_foldersuffix" >>$GITHUB_ENV
