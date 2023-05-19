# First argument is round number, second is output directory
if [ $# -ne 1 ]; then
    echo "Usage: $0 <round number>"
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
echo "Calculating for $date to $now"
echo "df_week_original: $df_week_original"

./dfpy_docker_past vebals $date $now 1 /app/data/$df_week_original 1
./dfpy_docker_past calculate_passive 1 $date /app/data/$df_week_original