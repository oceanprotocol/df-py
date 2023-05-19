mkdir -p /tmp/dfpy
date=`date -dlast-thursday '+%Y-%m-%d'`
now=`date '+%Y-%m-%d'`
nm=`date +%u`

if [ $nm -eq 4 ]
then
        date="$now"
fi
echo $date

dfpy_docker getrate OCEAN $date $now /app/data
dfpy_docker getrate ETH $date $now /app/data
dfpy_docker getrate BNB $date $now /app/data
dfpy_docker getrate EWT $date $now /app/data
dfpy_docker getrate MOVR $date $now /app/data
dfpy_docker getrate MATIC $date $now /app/data

dfpy_docker volsym $date latest 50 /app/data 1 && 
dfpy_docker volsym $date latest 50 /app/data 56 && 
dfpy_docker volsym $date latest 50 /app/data 137 &&
dfpy_docker volsym $date latest 50 /app/data 246 && 
dfpy_docker volsym $date latest 50 /app/data 1285 && 

dfpy_docker vebals  $date latest 50 /app/data 1 &&
dfpy_docker vebals  $date latest 1 /app/data 1 &&
dfpy_docker allocations $date latest 50 /app/data 1 
dfpy_docker allocations $date latest 1 /app/data 1

cp /tmp/dfpy/rate-OCEAN.csv /tmp/dfpy/rate-MOCEAN.csv
sed -i -e 's/MOCEAN/OCEAN/g' /tmp/dfpy/rate-MOCEAN.csv

dfpy_docker calc /app/data 0 $date OCEAN

dfpy_docker calculate_passive 1 $date /app/data

mv /tmp/dfpy/* ~/.dfcsv/
