for i in `seq 1 10`; do
curl -d 'entry=B-'${i} -X 'POST' 'http://127.0.0.1:61002/board'
done
#This will post entry=t1, entry=t2, ..., entry=t20 to http://ip:port/entries
