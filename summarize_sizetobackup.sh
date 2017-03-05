#!/bin/bash

sum=0

cd sizetobackup
for i in *; do
	b=$( cat $i )
	gb=$( bc -l <<< "scale=2; $b/1024/1024/1024" )
	sum=$( bc -l <<< "scale=2; $sum+$gb" )
	echo "$i: ${gb}GB"
done

echo "Total: ${sum}GB"
