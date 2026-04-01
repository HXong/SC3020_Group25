import psycopg2

def get_query_plan(query):
    
    conn = psycopg2.connect(database="TPC-H", user="postgres", password="postgres", host="localhost", port="5432")
    
    cur = conn.cursor()
    
    # Set up the query to retrieve the execution plan in JSON format.
    explain_query = f"EXPLAIN (FORMAT JSON, COSTS, VERBOSE) {query}"
    cur.execute(explain_query)
    
    # This returns the JSON plan
    plan = cur.fetchone()[0][0]["Plan"]
    
    cur.close()
    conn.close()
    print(plan)
    return plan

test_query = "SELECT * FROM customer C, orders O WHERE C.c_custkey = O.o_custkey"
full_plan = get_query_plan(test_query)