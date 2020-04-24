#!/bin/bash
source db_info.sh
# $1 is the container param. of the postgresql database
docker exec $1  pg_dump -U "${user}" "${db}" | gzip > backup.gz