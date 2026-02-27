# Basic Setup (Docker)

This setup avoids installing PostgreSQL locally.

## Prerequisites
- Docker Desktop installed and running

## Start PostgreSQL
From repo root:

```bash
docker compose up -d
```

PostgreSQL will be available at:
- Host: localhost
- Port: 5432
- User: postgres
- Password: postgres
- Database: sc3020_project1

## Create tables
### Option A (recommanded, using container psql):
```bash
docker exec -i sc3020_db psql -U postgres -d sc3020_project1 < sql/01_table_creation.sql
```
### Option B (if you prefer psql installed locally):
```bash
psql -h localhost -p 5432 -U postgres -d sc3020_project1 -f sql/01_table_creation.sql
```

## Import CSV data
Import the 8 CSV files using any method you prefer (pgAdmin GUI / COPY / psql \copy).

Each member should download the dataset from NTULearn and import
the data using their preferred method.

Recommended import order (due to FK constraints):

`region → nation → supplier → customer → part → partsupp → orders → lineitem`

## Stop / reset
### Stop containers:
```bash
docker compose down
```
---
---
### Reset DB without deleting container volume:
```bash
docker exec -i sc3020_db psql -U postgres -d sc3020_project1 < sql/00_drop_all.sql
```
Then recreate
```bash
docker exec -i sc3020_db psql -U postgres -d sc3020_project1 < sql/01_table_creation.sql
```
---
---
### Reset everything (delete DB volume):
```bash
docker compose down -v
```