for i in `seq 1 300`; do
curl -d 'entry=P-'${i} -X 'POST' 'http://127.0.0.1:61001/board'
done
#This will post entry=t1, entry=t2, ..., entry=t20 to http://ip:port/entries
