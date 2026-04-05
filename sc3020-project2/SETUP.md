# Basic Setup (Docker)

This setup avoids installing PostgreSQL locally.

## Prerequisites

- Docker Desktop installed and running
- Python 3.10+

## 1) Download and Generate TPC-H Data

Download from NTULearn (provided zip).

Extract it into project (follow the same instructions as per the project description)

### 1.1) Configure makefile.suite

Open `tpch/dbgen/makefile.suite`

Modify:
```Bash
DATABASE = POSTGRESQL
MACHINE = LINUX
WORKLOAD = TPCH
CC = gcc
```

### 1.2) Compile dbgen

```Bash
cd tpch/dbgen
make -f makefile.suite
```

Some versions of the TPC-H dbgen source contain legacy compiler macros that may fail under gcc. If build errors such as invalid uI64 suffixes appear, update the relevant integer definitions in config.h to long long int / ull / %lld equivalents before recompiling.

### 1.3) Generate Data

run `./dbgen -s 1` will generate all *.tbl files

### 1.4) Move data into project

Move all .tbl files into: "/data" located in our git project (sc3020-project2/data)

## 2) Setup Python Env

From project root: `python -m venv venv`

Activate:

- Windows: `venv\Scripts\activate`

- Mac/Linux: `source venv/bin/activate`

Install Dependencies:
`pip install -r requirements.txt`

## 3) Prepare Dataset 

Convert .tbl -> .csv and clean trailing pipes:
```bash
python project.py --setup-csv
```

This will:
- rename .tbl → .csv
- remove trailing |
- Optionally remove .tbl files if `python project.py --setup-csv --delete-tbl`



## 4) Start PostgreSQL

From repo root:

```bash
docker compose up -d
```

PostgreSQL will be available at:

- Host: localhost
- Port: 5432
- User: postgres
- Password: postgres
- Database: TPC-H

## 5) Create tables

### Option A (recommanded, using container psql):

```bash
docker exec -i sc3020_project2_db psql -U postgres -d TPC-H < sql/01_table_creation.sql
```

For windows, if "<" not working, use this:

```bash
docker cp sql/01_table_creation.sql sc3020_project2_db:/01_table_creation.sql
docker exec -it sc3020_project2_db psql -U postgres -d TPC-H
\i /01_table_creation.sql
```

---

### Option B (using pgAdmin) [HongXun]

1. Open pgAdmin in browser using this [localhost](http://localhost:5050)

- Login:
  - Email: admin@local.com
  - Password: admin

2. Add PostgreSQL Server in pgAdmin

- Right click `Servers`
- click Register -> Server
- General Tab
  - Name: `TPC-H`
- Connection Tab
  - Host: `db`
  - Port: `5432`
  - Username: `admin`
  - Password: `admin`

3. Create Tables using `01_table_creation.sql`

- Right click TPC-H (under database) -> Open Query tool
- Paste the entire contents of 01_table_creation.sql -> Click Execute Script
- Verify tables created, in pgAdmin expand:

```
Databases
 └── TPC-H
     └── Schemas
         └── public
             └── Tables
```

- Should see the 8 tables created

---

### Option C (if you prefer psql installed locally):

```bash
psql -h localhost -p 5432 -U postgres -d sc3020_project1 -f sql/01_table_creation.sql
```

## 6a) Import CSV data (using CLI)

Import the 8 CSV files using any method you prefer (pgAdmin GUI / COPY / psql \copy).

Each member should download the dataset from NTULearn and import
the data using their preferred method.

Recommended import order (due to FK constraints):

`region → nation → supplier → customer → part → partsupp → orders → lineitem`

Place your CSV in the `/data` folder

Then run (skip this step if you enter the container earlier):

```bash
docker exec -it sc3020_db psql -U postgres -d sc3020_project1
```

Inside psql:

```bash
\copy region FROM '/data/region.csv' WITH (FORMAT csv, DELIMITER '|', NULL '');
```

Run in this order:

```bash
\copy region   FROM '/data/region.csv'   WITH (FORMAT csv, DELIMITER '|', NULL '');
\copy nation   FROM '/data/nation.csv'   WITH (FORMAT csv, DELIMITER '|', NULL '');
\copy supplier FROM '/data/supplier.csv' WITH (FORMAT csv, DELIMITER '|', NULL '');
\copy customer FROM '/data/customer.csv' WITH (FORMAT csv, DELIMITER '|', NULL '');
\copy part     FROM '/data/part.csv'     WITH (FORMAT csv, DELIMITER '|', NULL '');
\copy partsupp FROM '/data/partsupp.csv' WITH (FORMAT csv, DELIMITER '|', NULL '');
\copy orders   FROM '/data/orders.csv'   WITH (FORMAT csv, DELIMITER '|', NULL '');
\copy lineitem FROM '/data/lineitem.csv' WITH (FORMAT csv, DELIMITER '|', NULL '');
```

Note:

- Since some of the files are very big, it will take some time. Docker should allocate
  enough memory for this. If unsure, check your docker desktop for memory usage.

## 6b) Import CSV data (using pgAdmin)

For each table:

1. Right click table → Import/Export Data
2. Choose:

- Format: CSV
- Filename: select corresponding CSV file
- Encoding: UTF-8
- Delimiter: |
- Header: no

Repeat for each table in the correct order due to FK constraints.

1. region
2. nation
3. supplier
4. customer
5. part
6. partsupp
7. orders
8. lineitem

Note:

- You can verify the imports by running select count for each table
- Some of the imports could take some time due to large number of rows.

## 7) Stop / reset

### Stop containers:

```bash
docker compose down
```

---

---

### Reset DB without deleting container volume:

```bash
docker exec -i sc3020_project2_db psql -U postgres -d TPC-H < sql/00_drop_all.sql
```

Then recreate

```bash
docker exec -i sc3020_project2_db psql -U postgres -d TPC-H < sql/01_table_creation.sql
```

---

---

### Reset everything (delete DB volume):

```bash
docker compose down -v
```
