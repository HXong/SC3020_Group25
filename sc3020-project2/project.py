import argparse
from pathlib import Path
import json

from preprocessing import setup_csv, get_qep, get_aqp_variants
from interface import launch_app
from annotation import generate_annotations


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

    args = parser.parse_args()

    if args.setup_csv:
        setup_csv(Path(args.data_folder))
        return
    
    if args.test_query:
        qep = get_qep(args.test_query)
        print(json.dumps(qep, indent=2))
        return

    if args.test_aqp:
        aqps = get_aqp_variants(args.test_aqp)
        print(json.dumps(aqps, indent=2))
        return
    
    if args.test_annotation:
        qep = get_qep(args.test_annotation)
        aqps = get_aqp_variants(args.test_annotation)
        annotations = generate_annotations(args.test_annotation, qep, aqps)
        print(json.dumps(annotations, indent=2))
        return

    launch_app()


if __name__ == "__main__":
    main()