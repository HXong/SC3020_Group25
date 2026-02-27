# Basic Setup (Docker)

This setup avoids installing PostgreSQL locally.

## Prerequisites
- Docker Desktop installed and running

## 1) Start PostgreSQL
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

## 2) Create tables
### Option A (recommanded, using container psql):
```bash
docker exec -i sc3020_db psql -U postgres -d sc3020_project1 < sql/01_table_creation.sql
```
For windows, if "<" not working, use this:
```bash
docker cp sql/01_table_creation.sql sc3020_db:/01_table_creation.sql
docker exec -it sc3020_db psql -U postgres -d sc3020_project1
\i /01_table_creation.sql
```
---
### Option B (if you prefer psql installed locally):
```bash
psql -h localhost -p 5432 -U postgres -d sc3020_project1 -f sql/01_table_creation.sql
```

## 3) Import CSV data
Import the 8 CSV files using any method you prefer (pgAdmin GUI / COPY / psql \copy).

Each member should download the dataset from NTULearn and import
the data using their preferred method.

Recommended import order (due to FK constraints):

`region → nation → supplier → customer → part → partsupp → orders → lineitem`

Place your CSV in the `/csv` folder

Then run (skip this step if you enter the container earlier):
```bash
docker exec -it sc3020_db psql -U postgres -d sc3020_project1
```

Inside psql:
```bash
\copy region FROM '/csv/region.csv' WITH (FORMAT csv, DELIMITER '|', NULL '');
```

Run in this order:
```bash
\copy region   FROM '/csv/region.csv'   WITH (FORMAT csv, DELIMITER '|', NULL '');
\copy nation   FROM '/csv/nation.csv'   WITH (FORMAT csv, DELIMITER '|', NULL '');
\copy supplier FROM '/csv/supplier.csv' WITH (FORMAT csv, DELIMITER '|', NULL '');
\copy customer FROM '/csv/customer.csv' WITH (FORMAT csv, DELIMITER '|', NULL '');
\copy part     FROM '/csv/part.csv'     WITH (FORMAT csv, DELIMITER '|', NULL '');
\copy partsupp FROM '/csv/partsupp.csv' WITH (FORMAT csv, DELIMITER '|', NULL '');
\copy orders   FROM '/csv/orders.csv'   WITH (FORMAT csv, DELIMITER '|', NULL '');
\copy lineitem FROM '/csv/lineitem.csv' WITH (FORMAT csv, DELIMITER '|', NULL '');
```
Note:
- Since some of the files are very big, it will take some time. Docker should allocate
enough memory for this. If unsure, check your docker desktop for memory usage.

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