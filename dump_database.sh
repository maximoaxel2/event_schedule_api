#!/bin/bash

if [ ! -f .env ]; then
  echo "Error: .env file not found."
  exit 1
fi

set -a
source .env
set +a

pg_dump "$DATABASE_URL" --no-data -O -x | grep -v "^--" | grep -v "SET" | grep -Ev '^\\' | cat -s > ./postgres_db.sql

echo "Database dumped."