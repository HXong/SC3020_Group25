import argparse
from pathlib import Path
from typing import Optional
import json

from preprocessing import setup_csv, get_qep, get_aqp_variants
from interface import launch_app
from annotation import generate_annotations


def process_query(query: str) -> dict:
    try:
        qep = get_qep(query)
        aqps = get_aqp_variants(query)
        annotation_result = generate_annotations(query, qep, aqps)

        return {
            "success": True,
            "query": query,
            "annotated_query": annotation_result["annotated_query"],
            "plan_summary": {
                "root_node_type": qep.get("Node Type"),
                "total_cost": qep.get("Total Cost"),
            },
            "raw_qep": qep,
            "raw_aqps": aqps,
            "plan_annotations": annotation_result.get("plan_annotations"),
            "error": None,
        }

    except Exception as e:
        return {
            "success": False,
            "query": query,
            "annotated_query": None,
            "plan_summary": None,
            "raw_qep": None,
            "raw_aqps": None,
            "plan_annotations": None,
            "error": str(e),
        }
    
def emit_output(data: dict, output_file: Optional[str], append: bool = False) -> None:
    if output_file:
        path = Path(output_file)
        path.parent.mkdir(parents=True, exist_ok=True)

        if append:
            with path.open("a", encoding="utf-8") as f:
                f.write(json.dumps(data))
                f.write("\n")
            print(f"Output appended to {path}")
        else:
            with path.open("w", encoding="utf-8") as f:
                json.dump(data, f, indent=2)
            print(f"Output written to {path}")
    else:
        print(json.dumps(data, indent=2))

def main() -> None:
    parser = argparse.ArgumentParser(description="SC3020 Project 2")
    parser.add_argument(
        "--setup-csv",
        action="store_true",
        help="Convert .tbl files to cleaned .csv files by removing trailing pipe characters"
    )
    parser.add_argument(
        "--delete-tbl",
        action="store_true",
        help="Delete original .tbl files after successful CSV creation"
    )
    parser.add_argument(
        "--data-folder",
        default="data",
        help="Path to folder containing TPC-H data files"
    )
    parser.add_argument(
        "--test-query",
        type=str,
        help="Run EXPLAIN (FORMAT JSON) on a query and print the QEP"
    )
    parser.add_argument(
        "--test-aqp",
        type=str,
        help="Run alternative-plan generation on a query and print AQPs"
    )
    parser.add_argument(
        "--test-annotation",
        type=str,
        help="Generate annotations for a query and print the result"
    )

    parser.add_argument(
        "--output-file",
        type=str,
        help="Write output JSON to a file instead of printing to terminal"
    )

    parser.add_argument(
        "--append-output",
        action="store_true",
        help="Append output to the specified file instead of overwriting it"
    )

    args = parser.parse_args()

    if args.setup_csv:
        setup_csv(Path(args.data_folder), delete_tbl=args.delete_tbl)
        return
    
    if args.test_query:
        qep = get_qep(args.test_query)
        emit_output(qep, args.output_file, args.append_output)
        return

    if args.test_aqp:
        aqps = get_aqp_variants(args.test_aqp)
        emit_output(aqps, args.output_file, args.append_output)
        return
    
    if args.test_annotation:
        result = process_query(args.test_annotation)
        emit_output(result, args.output_file, args.append_output)
        return

    launch_app(process_query)


if __name__ == "__main__":
    main()