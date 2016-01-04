#!/bin/bash
# Usage: <csv filename> <tablename>
tail --lines=+2 --silent $1 | sed -e "s/^/\'/;s/,/\',\'/g;s/$/\'/;s///g" > /tmp/g.$$
echo "use bender;"
echo "LOCK TABLES $2 WRITE;"
IFS="
"
for line in `cat /tmp/g.$$`
do
 echo "INSERT INTO \`"$2"\` VALUES ($line);"
done
echo "exit"
