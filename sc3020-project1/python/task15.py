import time
import random

import psycopg # PostgreSQL database adapter for Python

# 1. Open a connection
conn = psycopg.connect(
    host="localhost",
    port=5432,
    dbname="sc3020_project1",
    user="postgres",
    password="postgres"
)

#2. Issue the bulk query on a table without indexes
with conn.cursor() as cur:
    cur.execute("DROP TABLE IF EXISTS t2;")
    cur.execute("CREATE TABLE t2(a integer, b integer, c integer, d integer, e integer, primary key(a, b, c, d, e));")
    start = time.perf_counter()
    cur.execute("INSERT INTO t2 SELECT (floor(random()*10000)+1)::int, (floor(random()*10000)+1)::int,(floor(random()*10000)+1)::int, (floor(random()*10000)+1)::int,(floor(random()*10000)+1)::int FROM GENERATE_SERIES(1, 1000000);")
    end = time.perf_counter()
    print(f"Index-less Bulk Time: {end - start} seconds")
    cur.execute("COMMIT;")

# 4. Close the connection
conn.close()