#!/bin/bash

if [ ! -f .env ]; then
  echo "Error: .env file not found."
  exit 1
fi

set -a
source .env
set +a

pg_dump "$DATABASE_URL" -s --no-data -O -x | grep -v "^--" | grep -v "SET" | grep -Ev '^\\' | grep -v "^SELECT pg" | sed 's/public\.//g' | cat -s > ./postgres_db.sql

echo "Database dumped."