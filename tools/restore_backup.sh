#!/bin/bash
source db_info.sh
# $1 is the container param. of the postgresql database
docker exec -i $1  psql -U "${user}" -d "${db}" < gunzip backup.gz