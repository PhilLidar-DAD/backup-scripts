#!/bin/bash

sum=0

cd totalsize
for i in *; do
	b=$( cat $i )
	tb=$( bc -l <<< "scale=2; $b/1024/1024/1024/1024" )
	sum=$( bc -l <<< "scale=2; $sum+$tb" )
	echo "$i: ${tb}TB"
done

echo "Total: ${sum}TB"
