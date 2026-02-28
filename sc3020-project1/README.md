# SC3020 Project 1 (PostgreSQL)

Minimal shared repo for:
- common environment setup (Docker)
- shared SQL table creation
- shared folders for screenshots + report drafts/final

Each member can create their own task-specific SQL/scripts locally or in their own branches/folders if needed.

---

## Group Members

| Name | Matric No | Tasks |
|------|-----------|---------------|
| Member 1 | | |
| Member 2 | | |
| Member 3 | | |
| Member 4 | | |
| Member 5 | | |

---

## Repo layout
- `sql/` : shared SQL (only the common baseline)
- `screenshots/` : evidence screenshots, organised by task
- `report/` : report drafts + final PDF

## Quick start
Follow [setup instructions](SETUP.md).

## Notes
- Import the 8 CSV files into the 8 relations after table creation.
- Recommended import order (to satisfy FK constraints):
  `region → nation → supplier → customer → part → partsupp → orders → lineitem`