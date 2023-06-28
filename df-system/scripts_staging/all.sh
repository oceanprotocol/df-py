cd /app/df-py/
date=`date -dlast-thursday '+%Y-%m-%d'`
now=`date '+%Y-%m-%d'`
nm=`date +%u`

if [ $nm -eq 4 ]
then
        date="$now"
fi
echo $date


/app/df-py/dfpy_docker getrate OCEAN $date $now /app/data
/app/df-py/dfpy_docker getrate ETH $date $now /app/data
/app/df-py/dfpy_docker getrate MATIC $date $now /app/data


/app/df-py/dfpy_docker volsym $date latest 50 /app/data 80001 && 
/app/df-py/dfpy_docker volsym $date latest 50 /app/data 5

/app/df-py/dfpy_docker vebals  $date latest 50 /app/data 5 &&
/app/df-py/dfpy_docker vebals  $date latest 1 /app/data 5 &&
/app/df-py/dfpy_docker allocations $date latest 50 /app/data 5
/app/df-py/dfpy_docker allocations $date latest 1 /app/data 5
/app/df-py/dfpy_docker calculate_passive 5 $now /app/data


cp /tmp/dfpy/rate-OCEAN.csv /tmp/dfpy/rate-MOCEAN.csv
sed -i -e 's/MOCEAN/OCEAN/g' /tmp/dfpy/rate-MOCEAN.csv

/app/df-py/dfpy_docker calc /app/data 10000 OCEAN

mv /tmp/dfpy/* ~/.dfcsv/