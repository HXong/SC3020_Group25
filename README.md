# SQL Query Plan Analyzer & Visualizer (SC3020)

A system that extracts, analyzes, and explains PostgreSQL Query Execution Plans (QEP) through **clause-level annotations and graph visualization**.

This project is split into two parts:

- **Project 1** → Query Plan Extraction & Visualization  
- **Project 2** → Clause-Level Annotation Engine  

---

## Features

- Extract Query Execution Plans using PostgreSQL `EXPLAIN (FORMAT JSON)`
- Map SQL clauses → physical operators (Scan, Join, Aggregate, etc.)
- Explain **WHY operators are chosen** (cost-based reasoning)
- Interactive GUI for:
  - Query input
  - Execution plan visualization
  - Human-readable annotations
- Graph-based visualization of execution plans (NetworkX + Matplotlib)

---

## Project 1 – Query Plan Visualization

### Objective
Convert PostgreSQL execution plans into an interpretable graph.

### Key Components
- Parse JSON QEP output
- Construct directed graph (operator tree)
- Visualize using NetworkX

### Example Output
- Sequential Scan
- Hash Join
- Aggregate
- Sort / Limit

---

## Project 2 – Clause-Level Annotation Engine

### Objective
Explain how SQL clauses map to physical execution steps.

### Key Capabilities

- `[FROM]` → Scan type detection (Seq Scan, Index Scan)
- `[WHERE]` → Predicate binding
- `[JOIN]` → Join operator identification
- `[GROUP BY]` → Aggregate mapping
- `[ORDER BY]` → Sort detection

---

## Key Design Highlights

### 1. Condition Normalization
- Handles SQL vs PostgreSQL format differences  
- Supports:
  - Equality (`=`)  
  - Range (`>`, `<`, `>=`, `<=`)  
  - BETWEEN → converted to range  

---

### 2. Predicate Matching Engine
- Canonical comparison between:
  - SQL query conditions
  - Plan predicates
- Avoids strict string matching → improves generality

---

### 3. Cost-Based Explanation
Example:
- Hash Join selected over Nested Loop
- because estimated cost is lower


---

## GUI Overview

- SQL input editor
- Annotation panel
- Execution plan graph

---

## Setup (Summary)

- Requires local PostgreSQL
- Load TPC-H dataset
- Update `connect_db()` if needed
- Run: python project.py


> Full setup guide provided in separate document.

---

## Limitations

- Depends on PostgreSQL plan output format
- Limited support for complex expressions (e.g. nested subqueries)
- Visualization may overlap for large plans

---

## Learning Outcomes

- Query Optimization Internals
- Cost-Based Decision Making
- SQL → Physical Plan Mapping
- System Design (modular pipeline)
- GUI + Data Visualization

---

## Group Members

| Name |
|------|
| Ong Hong Xun |
| Clarence Tan Yan Kai |
| Wong Rong Jing |
| Chen ZhongJiang |
| Chan Zi Jian |