#!/bin/bash
# Usage: [-u username -e database] tablename
DBUSER=bender
DATABASE=bender
TEMP=`getopt -o u:e: --long user:database: -n 'fetch-csv' -- "$@"`
eval set -- "$TEMP"
while getopts "u:e:" arg; do
    case $arg in
	u)
	    DBUSER=$OPTARG;;
	e)
	    DATABASE=$OPTARG;;
    esac
done
TABLE=$BASH_ARGV
shift
# echo DBUSER=${DBUSER} DATABASE=${DATABASE} TABLE=${TABLE} OPTIND=$OPTIND
if  [ -z "${DBUSER}" ] || [ -z "${DATABASE}" ] || [ -z "${TABLE}" ];
then
    echo 'Usage: fetch-csv [-u <database_username>] [-e <database>] tablename'
    exit 1
fi
# no way to tell mysql to use "," instead of <tab> as seperator?
mysql -u ${DBUSER} -p -B -e "use ${DATABASE}; select * from ${TABLE};" | sed -e 's/	/,/g'
