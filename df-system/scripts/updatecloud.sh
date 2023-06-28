#!/bin/bash

cd /root/.dfcsv/historical

file_count_before=$(ls -1 | wc -l)

gsutil rsync -r gs://df-historical-data .

file_count_after=$(ls -1 | wc -l)

if [ $file_count_before -ne $file_count_after ]; then
    echo "Files updated"
    # get the name of new file
    new_file=$(ls -t | head -1)

    # check if it's a directory
    if [ -d $new_file ]; then
        echo "New file is a directory"
        # copy nftinfo csvs
        cp /root/.dfcsv/nftinfo_* $new_file
        echo "Copied nftinfo csvs"
        count_start=$(date -d "2022-09-29" +%Y-%m-%d)
        now=$(date +%Y-%m-%d)
        df_week=$(($(($(($(($(date -d "$now" +%s) - $(date -d "$count_start" +%s))) / 86400)) / 7)) + 4))
        echo $df_week
        cd /app/df-py
        ./helperscript.sh $df_week
        cd -
    fi

#    exit 0
else
    echo "No files updated"
#    exit 1
fi
gsutil rsync -r . gs://df-historical-data