# SC3020 Project 2 (Query Annotation System)

This project implements a system to:
- analyze SQL queries using PostgreSQL execution plans
- generate clause-level annotations (scan, join, predicate, etc.)
- visualize query execution plans

For Development, this project will be done on `project2-main`. For local branches, you can merge new code changes into the main branch by requesting for PR.

---

## Group Members

| Name |
|------|
| Ong Hong Xun |
| Clarence Tan Yan Kai |
| Wong Rong Jing |
| Chen ZhongJiang |
| Chan Zi Jian |

---

## Repo layout
```bash
sql/            # table creation + schema scripts
data/           # dataset files (.tbl / .csv)
screenshots/    # evidence for report
report/         # report drafts + final PDF
```

---


## Setup
Follow [setup instructions](SETUP.md).

---

## Running the Project
### 1) Activate Python env
```bash
venv\Scripts\activate        # Windows
# or
source venv/bin/activate     # Mac/Linux
```

### 2) Run Backend (Annotation Engine)

Basic test
```bash
python project.py --test-annotation "SELECT * FROM customer WHERE c_custkey = 1;"
```

Save output to file
```bash
python project.py --test-annotation "SELECT * FROM customer;" --output-file outputs/result.json
```

Append multiple test runs
```bash
python project.py --test-annotation "SELECT * FROM customer;" --output-file outputs/tests.jsonl --append-output
```

### 3) Run GUI (Main task)
```bash
python project.py
```

Features:
- input SQL query
- visualize Query Execution Plan (QEP)
- backend annotation integration

## Notes
- Import the 8 CSV files into the 8 relations after table creation.
- Recommended import order (to satisfy FK constraints):
  `region → nation → supplier → customer → part → partsupp → orders → lineitem`
- Ensure database is fully loaded before running queries
- Queries are executed using PostgreSQL EXPLAIN (FORMAT JSON)
- Annotation system supports:
    - scans (seq / index)
    - joins(hash / merge / nested loop)
    - predicates (filter vs index condition)
    - GROUP BY
    - ORDER BY

## Limitations
- Subqueries (IN (SELECT ...)) are not fully supported
- Complex predicates may not always be annotated
- SQL parsing is regex-based (not a full SQL parser)