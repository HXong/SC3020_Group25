import re
from typing import Any, Dict, List, Optional


IGNORED_WRAPPER_NODES = {"Gather", "Hash", "Sort", "Materialize"}

# Plan Tree Helpers
def get_meaningful_node(plan: dict) -> dict:
    current = plan
    while current.get("Node Type") in IGNORED_WRAPPER_NODES and current.get("Plans"):
        current = current["Plans"][0]
    return current


def traverse_plan(plan: Dict[str, Any], results: List[Dict[str, Any]]) -> None:
    node_info = {
        "node_type": plan.get("Node Type"),
        "relation": plan.get("Relation Name"),
        "alias": plan.get("Alias"),
        "index_name": plan.get("Index Name"),
        "join_type": plan.get("Join Type"),
        "startup_cost": plan.get("Startup Cost"),
        "total_cost": plan.get("Total Cost"),
        "hash_cond": plan.get("Hash Cond"),
        "merge_cond": plan.get("Merge Cond"),
        "join_filter": plan.get("Join Filter"),
        "filter": plan.get("Filter"),
        "index_cond": plan.get("Index Cond"),
    }
    results.append(node_info)

    for child in plan.get("Plans", []):
        traverse_plan(child, results)


def extract_plan_operators(plan: Dict[str, Any]) -> List[Dict[str, Any]]:
    results: List[Dict[str, Any]] = []
    traverse_plan(plan, results)
    return results


# SQL Parsing Helpers
def normalize_whitespace(text: str) -> str:
    return " ".join(text.strip().split())

def split_sql_clauses(query: str) -> Dict[str, str]:
    query_clean = normalize_whitespace(query.strip().rstrip(";"))

    lower_query = query_clean.lower()

    from_pos = lower_query.find(" from ")
    where_pos = lower_query.find(" where ")
    group_by_pos = lower_query.find(" group by ")
    order_by_pos = lower_query.find(" order by ")

    result = {
        "select": "",
        "from": "",
        "where": "",
    }

    if from_pos == -1:
        result["select"] = query_clean
        return result

    result["select"] = query_clean[:from_pos].strip()

    clause_end_positions = [pos for pos in [where_pos, group_by_pos, order_by_pos] if pos != -1]
    from_end = min(clause_end_positions) if clause_end_positions else len(query_clean)

    result["from"] = query_clean[from_pos + len(" from "):from_end].strip()

    if where_pos != -1:
        where_end_candidates = [pos for pos in [group_by_pos, order_by_pos] if pos != -1 and pos > where_pos]
        where_end = min(where_end_candidates) if where_end_candidates else len(query_clean)
        result["where"] = query_clean[where_pos + len(" where "):where_end].strip()

    return result

def parse_from_items(from_clause: str) -> List[Dict[str, Optional[str]]]:
    if not from_clause:
        return []

    items = []
    parts = [part.strip() for part in from_clause.split(",")]

    for part in parts:
        tokens = part.split()

        table = None
        alias = None

        if len(tokens) == 1:
            table = tokens[0]
            alias = tokens[0]
        elif len(tokens) >= 2:
            table = tokens[0]
            if len(tokens) >= 3 and tokens[1].lower() == "as":
                alias = tokens[2]
            else:
                alias = tokens[1]

        items.append({
            "raw": part,
            "table": table.lower() if table else None,
            "alias": alias.lower() if alias else None,
            "annotation": None,
        })

    return items

def parse_table_alias(part: str) -> Dict[str, Optional[str]]:
    tokens = part.strip().split()

    table = None
    alias = None

    if len(tokens) == 1:
        table = tokens[0]
        alias = None
    elif len(tokens) >= 2:
        table = tokens[0]
        if len(tokens) >= 3 and tokens[1].lower() == "as":
            alias = tokens[2]
        else:
            alias = tokens[1]

    return {
        "raw": part.strip(),
        "table": table.lower() if table else None,
        "alias": alias.lower() if alias else None,
        "annotation": None,
    }


def parse_from_and_joins(from_clause: str) -> Dict[str, Any]:
    """
    Supports:
      FROM customer C, orders O
      FROM customer C JOIN orders O ON C.c_custkey = O.o_custkey
      FROM a JOIN b ON ... JOIN c ON ...

    Returns:
      {
          "from_items": [...],
          "join_conditions": [...]
      }
    """
    if not from_clause:
        return {"from_items": [], "join_conditions": []}

    # If there is no JOIN keyword, fall back to comma-separated parsing
    if " join " not in from_clause.lower():
        return {
            "from_items": parse_from_items(from_clause),
            "join_conditions": [],
        }

    from_items: List[Dict[str, Optional[str]]] = []
    join_conditions: List[Dict[str, Optional[str]]] = []

    # Split on JOIN boundaries
    join_parts = re.split(r"\bjoin\b", from_clause, flags=re.IGNORECASE)

    # First part is the initial FROM item
    first_part = join_parts[0].strip()
    if first_part:
        from_items.append(parse_table_alias(first_part))

    # Remaining parts should look like: "<table alias> ON <condition>"
    for part in join_parts[1:]:
        split_part = re.split(r"\bon\b", part, maxsplit=1, flags=re.IGNORECASE)

        table_part = split_part[0].strip()
        cond_part = split_part[1].strip() if len(split_part) > 1 else ""

        if table_part:
            from_items.append(parse_table_alias(table_part))

        if cond_part:
            join_conditions.append({
                "raw": cond_part,
                "annotation": None,
            })

    return {
        "from_items": from_items,
        "join_conditions": join_conditions,
    }

def split_where_conditions(where_clause: str) -> List[Dict[str, Optional[str]]]:
    if not where_clause:
        return []

    # split on AND
    conditions = [cond.strip() for cond in re.split(r"\band\b", where_clause, flags=re.IGNORECASE)]

    return [
        {
            "raw": cond,
            "annotation": None,
        }
        for cond in conditions if cond
    ]

def extract_sql_components(query: str) -> Dict[str, Any]:
    clauses = split_sql_clauses(query)
    from_info = parse_from_and_joins(clauses["from"])

    return {
        "select_clause": clauses["select"],
        "from_items": from_info["from_items"],
        "join_conditions": from_info["join_conditions"],
        "where_conditions": split_where_conditions(clauses["where"]),
        "raw_query": query.strip(),
    }


# Condition Normalisation Helpers
def normalize_identifier(identifier: str) -> str:
    return identifier.strip().strip("()").lower()


def canonicalize_equality_condition(condition: str) -> Optional[str]:
    """
    Convert equality predicates like:
    C.c_custkey = O.o_custkey
    (o.o_custkey = c.c_custkey)

    into a canonical order-independent string.
    """
    if not condition or "=" not in condition:
        return None

    cleaned = condition.strip().strip("()")
    parts = cleaned.split("=")

    if len(parts) != 2:
        return None

    left = normalize_identifier(parts[0])
    right = normalize_identifier(parts[1])

    ordered = sorted([left, right])
    return f"{ordered[0]} = {ordered[1]}"

def canonicalize_condition(condition: str) -> str:
    """
    Normalize a condition string for basic matching.
    Example:
      "(c_custkey = 1)" -> "c_custkey = 1"
      "C.c_custkey = O.o_custkey" -> "c.c_custkey = o.o_custkey"
    """
    cleaned = condition.strip().strip("()").lower()
    cleaned = re.sub(r"\s+", " ", cleaned)
    return cleaned


# Plan Semantic Analysis Helpers
def summarize_scan_operator(node: Dict[str, Any]) -> Optional[Dict[str, str]]:
    node_type = node.get("node_type")
    relation = node.get("relation")
    alias = node.get("alias")
    index_name = node.get("index_name")

    if not relation:
        return None

    if node_type == "Seq Scan":
        message = f"Table {relation} is accessed using sequential scan."
    elif node_type == "Index Scan":
        message = f"Table {relation} is accessed using index scan via {index_name}."
    elif node_type == "Index Only Scan":
        message = f"Table {relation} is accessed using index-only scan via {index_name}."
    elif node_type == "Bitmap Heap Scan":
        message = f"Table {relation} is accessed using bitmap heap scan."
    else:
        return None

    return {
        "relation": relation.lower(),
        "alias": alias.lower() if alias else None,
        "message": message,
    }


def summarize_join_operator(node: Dict[str, Any]) -> Optional[Dict[str, str]]:
    node_type = node.get("node_type")

    if node_type not in {"Hash Join", "Merge Join", "Nested Loop"}:
        return None

    cond = node.get("hash_cond") or node.get("merge_cond") or node.get("join_filter")
    message = f"This join is implemented using {node_type.lower()}."

    return {
        "node_type": node_type,
        "condition": cond,
        "message": message,
        "total_cost": node.get("total_cost"),
    }


def compare_join_alternatives(qep: Dict[str, Any], aqps: Dict[str, Any]) -> List[str]:
    messages = []

    qep_node_type = qep.get("Node Type")
    qep_cost = qep.get("Total Cost")

    if qep_node_type not in {"Hash Join", "Merge Join", "Nested Loop"}:
        return messages

    seen = set()

    for _, aqp_root in aqps.items():
        if not isinstance(aqp_root, dict):
            continue

        alt_node = get_meaningful_node(aqp_root)
        alt_node_type = alt_node.get("Node Type")
        alt_cost = aqp_root.get("Total Cost")

        if (
            alt_node_type != qep_node_type
            and alt_node_type in {"Hash Join", "Merge Join", "Nested Loop"}
            and alt_node_type not in seen
        ):
            messages.append(
                f"{qep_node_type} was selected over {alt_node_type} because its estimated cost "
                f"({qep_cost}) is lower than the alternative ({alt_cost})."
            )
            seen.add(alt_node_type)

    return messages

def summarize_predicate_usage(node: Dict[str, Any]) -> List[Dict[str, str]]:
    messages = []

    index_cond = node.get("index_cond")
    filter_cond = node.get("filter")

    if index_cond:
        messages.append({
            "condition": index_cond,
            "message": "This predicate is used as an index condition during execution."
        })

    if filter_cond:
        messages.append({
            "condition": filter_cond,
            "message": "This predicate is applied as a filter during execution."
        })

    return messages


def extract_plan_annotations(qep: Dict[str, Any], aqps: Dict[str, Any]) -> Dict[str, Any]:
    operators = extract_plan_operators(qep)

    scans = []
    joins = []
    predicates = []

    for op in operators:
        scan_info = summarize_scan_operator(op)
        if scan_info:
            scans.append(scan_info)

        join_info = summarize_join_operator(op)
        if join_info:
            joins.append(join_info)

        predicate_infos = summarize_predicate_usage(op)
        predicates.extend(predicate_infos)

    join_comparisons = compare_join_alternatives(qep, aqps)

    return {
        "scans": scans,
        "joins": joins,
        "predicates": predicates,
        "join_comparisons": join_comparisons,
        "operators": operators,
    }


# Bind Plan Annotation to SQL Components
def bind_scan_annotations(from_items: List[Dict[str, Any]], scans: List[Dict[str, str]]) -> None:
    for from_item in from_items:
        table = from_item.get("table")
        alias = from_item.get("alias")

        for scan in scans:
            if scan["relation"] == table or (scan["alias"] and scan["alias"] == alias):
                from_item["annotation"] = scan["message"]
                break


def bind_join_annotations_to_conditions(
    conditions: List[Dict[str, Any]],
    joins: List[Dict[str, str]],
    join_comparisons: List[str],
) -> None:
    comparison_text = " ".join(join_comparisons).strip()

    for condition_item in conditions:
        raw = condition_item["raw"]
        canonical_sql = canonicalize_equality_condition(raw)

        if not canonical_sql:
            continue

        for join in joins:
            join_cond = join.get("condition")
            canonical_plan = canonicalize_equality_condition(join_cond) if join_cond else None

            if canonical_plan and canonical_plan == canonical_sql:
                message = join["message"]
                if comparison_text:
                    message = f"{message} {comparison_text}"
                condition_item["annotation"] = message
                break

def bind_predicate_annotations(
    where_conditions: List[Dict[str, Any]],
    predicates: List[Dict[str, str]],
) -> None:
    for where_item in where_conditions:
        if where_item.get("annotation"):
            continue

        raw = where_item["raw"]
        canonical_sql = canonicalize_condition(raw)

        for predicate in predicates:
            plan_cond = predicate.get("condition")
            if not plan_cond:
                continue

            canonical_plan = canonicalize_condition(plan_cond)

            if canonical_plan == canonical_sql:
                where_item["annotation"] = predicate["message"]
                break


def bind_annotations_to_query(sql_components: Dict[str, Any], plan_annotations: Dict[str, Any]) -> Dict[str, Any]:
    bind_scan_annotations(sql_components["from_items"], plan_annotations["scans"])

    # First bind join annotations to explicit JOIN ... ON ...
    bind_join_annotations_to_conditions(
        sql_components["join_conditions"],
        plan_annotations["joins"],
        plan_annotations["join_comparisons"],
    )

    # Next bind to WHERE conditions for comma joins
    bind_join_annotations_to_conditions(
        sql_components["where_conditions"],
        plan_annotations["joins"],
        plan_annotations["join_comparisons"],
    )

    bind_predicate_annotations(
        sql_components["where_conditions"],
        plan_annotations["predicates"],
    )

    return sql_components



# Main Entry Point
def generate_annotations(query: str, qep: Dict[str, Any], aqps: Dict[str, Any]) -> Dict[str, Any]:
    sql_components = extract_sql_components(query)
    plan_annotations = extract_plan_annotations(qep, aqps)
    annotated_query = bind_annotations_to_query(sql_components, plan_annotations)

    return {
        "annotated_query": annotated_query,
        "plan_annotations": plan_annotations,
    }