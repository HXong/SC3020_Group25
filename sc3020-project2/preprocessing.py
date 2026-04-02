from pathlib import Path
import psycopg2
import json
from typing import Any, Dict, List

def convert_tbl_to_csv(tbl_path: Path) -> None:
    csv_path = tbl_path.with_suffix(".csv")
    line_count = 0

    with tbl_path.open("r", encoding="utf-8") as src, \
         csv_path.open("w", encoding="utf-8", newline="") as dst:
        for line in src:
            line = line.rstrip("\r\n")
            if line.endswith("|"):
                line = line[:-1]
            dst.write(line + "\n")
            line_count += 1

    print(f"Created {csv_path.name} from {tbl_path.name} ({line_count} lines)")


def setup_csv(data_folder: Path, delete_tbl: bool = False) -> None:
    if not data_folder.exists():
        print("Data folder not found.")
        return

    tbl_files = list(data_folder.glob("*.tbl"))
    if not tbl_files:
        print("No .tbl files found.")
        return

    converted_files = []

    for tbl_file in tbl_files:
        csv_path = convert_tbl_to_csv(tbl_file)
        converted_files.append((tbl_file, csv_path))

    if delete_tbl:
        for tbl_file, _ in converted_files:
            tbl_file.unlink()
            print(f"Deleted {tbl_file.name}")

    print("CSV setup done.")

def connect_db():
    return psycopg2.connect(
        host="localhost",
        port=5432,
        database="TPC-H",
        user="postgres",
        password="postgres"
    )

def get_qep(query: str) -> List[Dict[str, Any]]:
    """
    Get the Query Execution Plan (QEP) in JSON format.
    """
    conn = connect_db()
    cur = conn.cursor()

    cur.execute(f"EXPLAIN (FORMAT JSON) {query}")
    plan = cur.fetchone()[0][0]["Plan"]

    cur.close()
    conn.close()

    return plan

def get_aqp_variants(query: str) -> Dict[str, Any]:
    """
    Generate alternative query plans by disabling certain planner options.
    """
    conn = connect_db()
    cur = conn.cursor()

    aqps = {}

    planner_settings = {
        "no_seqscan": "SET enable_seqscan = off;",
        "no_indexscan": "SET enable_indexscan = off;",
        "no_hashjoin": "SET enable_hashjoin = off;",
        "no_mergejoin": "SET enable_mergejoin = off;",
        "no_nestloop": "SET enable_nestloop = off;"
    }

    for key, setting in planner_settings.items():
        try:
            cur.execute("RESET ALL;")
            cur.execute(setting)

            cur.execute(f"EXPLAIN (FORMAT JSON) {query}")
            aqps[key] = cur.fetchone()[0][0]["Plan"]

        except Exception as e:
            aqps[key] = str(e)

    cur.execute("RESET ALL;")
    cur.close()
    conn.close()

    return aqps

if __name__ == "__main__":
    # 1. Clean CSVs
    setup_csv(Path("data"))

    # 2. Test query plan
    test_query = "SELECT * FROM customer WHERE c_custkey = 1;"

    print("\nQEP:")
    qep = get_qep(test_query)
    print(json.dumps(qep, indent=2))

    print("\nAQPs:")
    aqps = get_aqp_variants(test_query)
    for k, v in aqps.items():
        print(f"\n--- {k} ---")
        print(json.dumps(v, indent=2))