mkdir -p /tmp/dfpy
dfpy_docker nftinfo /app/data 1
dfpy_docker nftinfo /app/data 137
mv /tmp/dfpy/nftinfo* ~/.dfcsv