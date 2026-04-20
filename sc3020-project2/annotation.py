import re
from typing import Any, Dict, List, Optional


IGNORED_WRAPPER_NODES = {"Gather", "Hash", "Materialize"}

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
        "recheck_cond": plan.get("Recheck Cond"),
        "sort_key": plan.get("Sort Key"),
        "child_plans": plan.get("Plans", []),
    }
    results.append(node_info)

    for child in plan.get("Plans", []):
        traverse_plan(child, results)


def extract_plan_operators(plan: Dict[str, Any]) -> List[Dict[str, Any]]:
    results: List[Dict[str, Any]] = []
    traverse_plan(plan, results)
    return results

def extract_order_by_column(expr: str) -> str:
    expr = expr.strip().lower()
    if "." in expr:
        expr = expr.split(".")[-1]
    return expr

def extract_column_from_index_cond(cond: str) -> Optional[str]:
    if not cond:
        return None

    cond = cond.strip().strip("()").lower()

    parts = cond.split("=")
    if len(parts) != 2:
        return None

    return normalize_identifier(parts[0])


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
    limit_pos = lower_query.find(" limit ")

    result = {
        "select": "",
        "from": "",
        "where": "",
        "group_by": "",
        "order_by": "",
        "limit": "",
    }

    if from_pos == -1:
        result["select"] = query_clean
        return result

    result["select"] = query_clean[:from_pos].strip()

    clause_end_positions = [
        pos for pos in [where_pos, group_by_pos, order_by_pos, limit_pos]
        if pos != -1
    ]
    from_end = min(clause_end_positions) if clause_end_positions else len(query_clean)
    result["from"] = query_clean[from_pos + len(" from "):from_end].strip()

    if where_pos != -1:
        where_end_candidates = [
            pos for pos in [group_by_pos, order_by_pos, limit_pos]
            if pos != -1 and pos > where_pos
        ]
        where_end = min(where_end_candidates) if where_end_candidates else len(query_clean)
        result["where"] = query_clean[where_pos + len(" where "):where_end].strip()

    if group_by_pos != -1:
        group_by_end_candidates = [
            pos for pos in [order_by_pos, limit_pos]
            if pos != -1 and pos > group_by_pos
        ]
        group_by_end = min(group_by_end_candidates) if group_by_end_candidates else len(query_clean)
        result["group_by"] = query_clean[group_by_pos + len(" group by "):group_by_end].strip()

    if order_by_pos != -1:
        order_by_end_candidates = [
            pos for pos in [limit_pos]
            if pos != -1 and pos > order_by_pos
        ]
        order_by_end = min(order_by_end_candidates) if order_by_end_candidates else len(query_clean)
        result["order_by"] = query_clean[order_by_pos + len(" order by "):order_by_end].strip()

    if limit_pos != -1:
        result["limit"] = query_clean[limit_pos + len(" limit "):].strip()

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

def protect_between_and(where_clause: str) -> str:

    pattern = re.compile(
        r"\bbetween\b\s+.+?\s+\band\b\s+.+?(?=\s+\band\b\s+|$)",
        flags=re.IGNORECASE
    )

    protected = where_clause
    counter = 0

    while True:
        match = pattern.search(protected)
        if not match:
            break

        full_text = match.group(0)
        placeholder = f"__BETWEEN_AND_{counter}__"
        counter += 1

        replacement = re.sub(
            r"\band\b",
            placeholder,
            full_text,
            count=1,
            flags=re.IGNORECASE
        )

        protected = protected[:match.start()] + replacement + protected[match.end():]

    return protected


def restore_between_and(condition: str) -> str:
    return re.sub(r"__BETWEEN_AND_\d+__", "AND", condition)


def split_where_conditions(where_clause: str) -> List[Dict[str, Optional[str]]]:
    if not where_clause:
        return []

    protected = protect_between_and(where_clause)

    conditions = [
        cond.strip()
        for cond in re.split(r"\band\b", protected, flags=re.IGNORECASE)
    ]

    restored_conditions = []
    for cond in conditions:
        cond = restore_between_and(cond)
        if cond:
            restored_conditions.append({
                "raw": cond.strip(),
                "annotation": None,
            })

    return restored_conditions

def split_order_by_items(order_by_clause: str) -> List[Dict[str, Optional[str]]]:
    if not order_by_clause:
        return []

    items = [item.strip() for item in order_by_clause.split(",")]

    return [
        {
            "raw": item,
            "annotation": None,
        }
        for item in items if item
    ]

def split_group_by_items(group_by_clause: str) -> List[Dict[str, Optional[str]]]:
    if not group_by_clause:
        return []

    items = [item.strip() for item in group_by_clause.split(",")]

    return [
        {
            "raw": item,
            "annotation": None,
        }
        for item in items if item
    ]


def extract_sql_components(query: str) -> Dict[str, Any]:
    clauses = split_sql_clauses(query)
    from_info = parse_from_and_joins(clauses["from"])

    return {
        "select_clause": clauses["select"],
        "from_items": from_info["from_items"],
        "join_conditions": from_info["join_conditions"],
        "where_conditions": split_where_conditions(clauses["where"]),
        "group_by_conditions": split_group_by_items(clauses["group_by"]),
        "order_by_conditions": split_order_by_items(clauses["order_by"]),
        "limit_clause": clauses["limit"],
        "raw_query": query.strip(),
    }


# Condition Normalisation Helpers
def normalize_identifier(identifier: str) -> str:
    identifier = identifier.strip().strip("()").lower()
    if "." in identifier:
        identifier = identifier.split(".")[-1]
    return identifier


def normalize_literal(value: str) -> str:
    value = value.strip()
    value = re.sub(r"::[a-zA-Z_]+", "", value)

    # strip one pair of surrounding quotes for simple literals
    if len(value) >= 2 and value[0] == "'" and value[-1] == "'":
        value = value[1:-1]

    return value.lower()


def canonicalize_and_condition(condition: str) -> Optional[str]:
    if not condition:
        return None

    cleaned = condition.strip().strip("()").lower()
    cleaned = re.sub(r"::[a-zA-Z_]+", "", cleaned)
    cleaned = re.sub(r"\s+", " ", cleaned)

    parts = re.split(r"\band\b", cleaned)

    normalized_parts = []
    for part in parts:
        part = part.strip()
        norm = canonicalize_generic_condition(part)
        if norm:
            normalized_parts.append(norm)

    return " AND ".join(sorted(normalized_parts)) if normalized_parts else None

def canonicalize_between_condition(condition: str) -> Optional[str]:
    """
    Normalize BETWEEN predicates.
    Example:
      l_shipdate BETWEEN '1994-01-01' AND '1994-12-31'
    """
    if not condition:
        return None

    cleaned = condition.strip().strip("()").lower()
    cleaned = re.sub(r"\s+", " ", cleaned)

    match = re.fullmatch(
        r"(.+?)\s+between\s+(.+?)\s+and\s+(.+)",
        cleaned,
        flags=re.IGNORECASE
    )
    if not match:
        return None

    left = normalize_identifier(match.group(1))
    low = match.group(2).strip()
    high = match.group(3).strip()

    return f"{left} between {low} and {high}"

def canonicalize_equality_condition(condition: str) -> Optional[str]:
    if not condition or "=" not in condition:
        return None

    cleaned = condition.strip().strip("()")
    parts = cleaned.split("=")

    if len(parts) != 2:
        return None

    left = normalize_identifier(parts[0])
    right = normalize_identifier(parts[1])

    return " = ".join(sorted([left, right]))

def canonicalize_like_condition(condition: str) -> Optional[str]:
    if not condition:
        return None

    cleaned = condition.strip().strip("()").lower()
    cleaned = re.sub(r"::[a-zA-Z_]+", "", cleaned)
    cleaned = re.sub(r"\s+", " ", cleaned)

    match = re.fullmatch(r"(.+?)\s+(like|ilike|~~|~~\*)\s+(.+)", cleaned)
    if not match:
        return None

    left = normalize_identifier(match.group(1))
    op = match.group(2)
    right = normalize_literal(match.group(3))

    # normalize postgres internal operators
    if op == "~~":
        op = "like"
    elif op == "~~*":
        op = "ilike"

    return f"{left} {op} {right}"

def canonicalize_generic_condition(condition: str) -> Optional[str]:
    """
    Normalize general predicates such as:
      c_acctbal > 1000
      o_orderdate <= '1995-01-01'
    """
    if not condition:
        return None

    cleaned = condition.strip().strip("()").lower()
    cleaned = re.sub(r"::[a-zA-Z_]+", "", cleaned)
    cleaned = re.sub(r"\s+", " ", cleaned)

    match = re.fullmatch(r"(.+?)\s*(>=|<=|!=|=|>|<)\s*(.+)", cleaned)
    if not match:
        return None

    left = normalize_identifier(match.group(1))
    op = match.group(2)
    right = match.group(3).strip()

    if is_identifier_like(right):
        right = normalize_identifier(right)
    else:
        right = normalize_literal(right)

    return f"{left} {op} {right}"

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

def is_identifier_like(expr: str) -> bool:
    """
    Returns True if the expression looks like a column reference,
    e.g. c.c_custkey or c_custkey
    """
    expr = expr.strip().strip("()").lower()

    # basic identifier / qualified identifier
    return bool(re.fullmatch(r"[a-z_][a-z0-9_]*(\.[a-z_][a-z0-9_]*)?", expr))

def is_join_like_condition(condition: str) -> bool:
    """
    Returns True if the condition looks like an equality join between two identifiers.
    Example:
      c.c_custkey = o.o_custkey   -> True
      c_custkey = o.o_custkey     -> True
      o_orderkey = 1              -> False
    """
    if not condition or "=" not in condition:
        return False

    cleaned = condition.strip().strip("()")
    parts = cleaned.split("=")

    if len(parts) != 2:
        return False

    left = parts[0].strip()
    right = parts[1].strip()

    return is_identifier_like(left) and is_identifier_like(right)

def expand_between_to_range(condition: str) -> Optional[str]:
    """
    Convert BETWEEN into equivalent range condition.
    """
    if not condition:
        return None

    cleaned = condition.strip().strip("()").lower()

    match = re.fullmatch(
        r"(.+?)\s+between\s+(.+?)\s+and\s+(.+)",
        cleaned,
        flags=re.IGNORECASE
    )
    if not match:
        return None

    col = normalize_identifier(match.group(1))
    low = match.group(2).strip()
    high = match.group(3).strip()

    return f"({col} >= {low}) and ({col} <= {high})"

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

    cond = (
        node.get("hash_cond")
        or node.get("merge_cond")
        or node.get("join_filter")
    )

    # Nested Loop fallback: infer join condition from child index conditions
    if not cond and node_type == "Nested Loop":
        for child in node.get("child_plans", []):
            child_index_cond = child.get("Index Cond")
            if child_index_cond and is_join_like_condition(child_index_cond):
                cond = child_index_cond
                break

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
    recheck_cond = node.get("recheck_cond")
    filter_cond = node.get("filter")

    if index_cond and not is_join_like_condition(index_cond):
        messages.append({
            "condition": index_cond,
            "message": "This predicate is used as an index condition during execution."
        })

    if recheck_cond and not is_join_like_condition(recheck_cond):
        messages.append({
            "condition": recheck_cond,
            "message": "This predicate is rechecked after index-based access."
        })

    if filter_cond and not is_join_like_condition(filter_cond):
        messages.append({
            "condition": filter_cond,
            "message": "This predicate is applied as a filter during execution."
        })

    return messages

def summarize_sort_operator(node: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    node_type = node.get("node_type")

    if node_type != "Sort":
        return None

    return {
        "sort_keys": node.get("sort_key", []),
        "message": "The result is sorted using a sort operator."
    }

def is_order_satisfied_by_index(
    order_by_conditions: List[Dict[str, Any]],
    operators: List[Dict[str, Any]],
) -> bool:
    if not order_by_conditions:
        return False

    for op in operators:
        if op.get("node_type") == "Index Scan" and op.get("index_name"):
            if op["index_name"].lower().endswith("_pkey"):
                return True

    return False

def summarize_aggregate_operator(node: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    node_type = node.get("node_type")

    if node_type not in {"Aggregate", "GroupAggregate", "HashAggregate"}:
        return None

    return {
        "node_type": node_type,
        "message": "Grouping is performed using an aggregate operator."
    }

def extract_plan_annotations(qep: Dict[str, Any], aqps: Dict[str, Any]) -> Dict[str, Any]:
    operators = extract_plan_operators(qep)

    scans = []
    joins = []
    predicates = []
    sorts = []
    aggregates = []

    for op in operators:
        scan_info = summarize_scan_operator(op)
        if scan_info:
            scans.append(scan_info)

        join_info = summarize_join_operator(op)
        if join_info:
            joins.append(join_info)

        predicate_infos = summarize_predicate_usage(op)
        predicates.extend(predicate_infos)

        sort_info = summarize_sort_operator(op)
        if sort_info:
            sorts.append(sort_info)

        aggregate_info = summarize_aggregate_operator(op)
        if aggregate_info:
            aggregates.append(aggregate_info)

    join_comparisons = compare_join_alternatives(qep, aqps)

    return {
        "scans": scans,
        "joins": joins,
        "predicates": predicates,
        "sorts": sorts,
        "aggregates": aggregates,
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

        if "select" in raw.lower():
            continue #skip subqueries

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
    for condition_item in where_conditions:
        raw = condition_item["raw"]

        canonical_sql_eq = canonicalize_equality_condition(raw)
        canonical_sql_generic = canonicalize_generic_condition(raw)
        canonical_sql_between_range = expand_between_to_range(raw)
        canonical_sql_between_norm = canonicalize_and_condition(canonical_sql_between_range)
        canonical_sql_like = canonicalize_like_condition(raw)

        for pred in predicates:
            plan_cond = pred.get("condition")
            if not plan_cond:
                continue

            canonical_plan_eq = canonicalize_equality_condition(plan_cond)
            canonical_plan_generic = canonicalize_generic_condition(plan_cond)
            canonical_plan_and = canonicalize_and_condition(plan_cond)
            canonical_plan_like = canonicalize_like_condition(plan_cond)

            if (
                canonical_sql_eq and canonical_plan_eq and canonical_sql_eq == canonical_plan_eq
            ) or (
                canonical_sql_generic and canonical_plan_generic and canonical_sql_generic == canonical_plan_generic
            ) or (
                canonical_sql_between_norm and canonical_plan_and and canonical_sql_between_norm == canonical_plan_and
            ) or (
                canonical_sql_like and canonical_plan_like and canonical_sql_like == canonical_plan_like
            ):
                condition_item["annotation"] = pred["message"]
                break

def bind_sort_annotations(
    order_by_conditions: List[Dict[str, Any]],
    sorts: List[Dict[str, Any]],
    operators: List[Dict[str, Any]],
) -> None:
    if not order_by_conditions:
        return

    # Case 1: explicit Sort node exists
    if sorts:
        for order_item in order_by_conditions:
            order_item["annotation"] = sorts[0]["message"]
        return

    # Case 2: ordering satisfied by index scan
    if is_order_satisfied_by_index(order_by_conditions, operators):
        for order_item in order_by_conditions:
            order_item["annotation"] = (
                "The ordering is satisfied by scanning an index in order, "
                "so no explicit sort operator is needed."
            )

def bind_group_by_annotations(
    group_by_conditions: List[Dict[str, Any]],
    aggregates: List[Dict[str, Any]],
) -> None:
    if not group_by_conditions or not aggregates:
        return

    for group_item in group_by_conditions:
        group_item["annotation"] = aggregates[0]["message"]


def bind_annotations_to_query(sql_components: Dict[str, Any], plan_annotations: Dict[str, Any]) -> Dict[str, Any]:
    bind_scan_annotations(sql_components["from_items"], plan_annotations["scans"])

    bind_join_annotations_to_conditions(
        sql_components["join_conditions"],
        plan_annotations["joins"],
        plan_annotations["join_comparisons"],
    )

    bind_join_annotations_to_conditions(
        sql_components["where_conditions"],
        plan_annotations["joins"],
        plan_annotations["join_comparisons"],
    )

    bind_predicate_annotations(
        sql_components["where_conditions"],
        plan_annotations["predicates"],
    )

    bind_group_by_annotations(
        sql_components["group_by_conditions"],
        plan_annotations["aggregates"],
    )

    bind_sort_annotations(
        sql_components["order_by_conditions"],
        plan_annotations["sorts"],
        plan_annotations["operators"],
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