for i in `seq 1 10`; do
curl -d 'entry=B-'${i} -X 'POST' 'http://10.1.0.2:61001/board'
done
#This will post entry=t1, entry=t2, ..., entry=t20 to http://ip:port/entries
