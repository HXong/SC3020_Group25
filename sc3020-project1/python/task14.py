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

#2. Issue the bulk query
with conn.cursor() as cur:
    cur.execute("DROP TABLE IF EXISTS t1;")
    cur.execute("CREATE TABLE t1(a integer, b integer, c integer, d integer, e integer, primary key(a, b, c, d, e));")
    cur.execute("CREATE INDEX idx_t1_a on t1(a);")
    cur.execute("CREATE INDEX idx_t1_b on t1(b);")
    cur.execute("CREATE INDEX idx_t1_c on t1(c);")
    cur.execute("CREATE INDEX idx_t1_d on t1(d);")
    cur.execute("CREATE INDEX idx_t1_e on t1(e);")
    start = time.perf_counter()
    cur.execute("INSERT INTO t1 SELECT (floor(random()*10000)+1)::int, (floor(random()*10000)+1)::int,(floor(random()*10000)+1)::int, (floor(random()*10000)+1)::int,(floor(random()*10000)+1)::int FROM GENERATE_SERIES(1, 1000000);")
    end = time.perf_counter()
    print(f"Bulk Time: {end - start} seconds")
    cur.execute("COMMIT;")

#3. Issue many individual queries
with conn.cursor() as cur:
    start = time.perf_counter()
    for i in range(1000000):
        a = random.randint(1, 10000)
        b = random.randint(1, 10000)
        c = random.randint(1, 10000)
        d = random.randint(1, 10000)
        e = random.randint(1, 10000)
        
        # issue a statement here to insert a tuple (a, b, c, d, e)
        cur.execute("INSERT INTO t1 VALUES (%s, %s, %s, %s, %s);", (a, b, c, d, e))

    end = time.perf_counter()
    print(f"Individual Time: {end - start} seconds")

# 4. Close the connection
conn.close()