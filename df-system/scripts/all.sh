mkdir -p /tmp/dfpy
date=`date -dlast-thursday '+%Y-%m-%d'`
now=`date '+%Y-%m-%d'`
nm=`date +%u`

if [ $nm -eq 4 ]
then
        date="$now"
fi
echo $date

dfpy_docker get_rate OCEAN $date $now /app/data
dfpy_docker get_rate ETH $date $now /app/data
dfpy_docker get_rate MATIC $date $now /app/data

dfpy_docker volsym $date latest 50 /app/data 1 &&
dfpy_docker volsym $date latest 50 /app/data 137 &&

dfpy_docker vebals  $date latest 50 /app/data 1 &&
dfpy_docker vebals  $date latest 1 /app/data 1 &&
dfpy_docker allocations $date latest 50 /app/data 1
dfpy_docker allocations $date latest 1 /app/data 1

cp /tmp/dfpy/rate-OCEAN.csv /tmp/dfpy/rate-MOCEAN.csv
sed -i -e 's/MOCEAN/OCEAN/g' /tmp/dfpy/rate-MOCEAN.csv

dfpy_docker calc volume /app/data 0 $date OCEAN

dfpy_docker calculate_passive 1 $date /app/data

mv /tmp/dfpy/* ~/.dfcsv/
