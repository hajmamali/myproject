from __future__ import annotations

import argparse
from pathlib import Path

from .baseline import compare_baseline, create_baseline
from .config import GovernanceConfig
from .engine import GovernanceEngine
from .reporters.html import write_html_report
from .reporters.json import write_json_report
from .reporters.junit import write_junit_report
from .reporters.markdown import write_markdown_report
from .reporters.sarif import write_sarif_report
from .reporters.text import write_text_report


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="governance")
    subparsers = parser.add_subparsers(dest="command", required=True)

    scan_parser = subparsers.add_parser("scan")
    scan_parser.add_argument("path", nargs="?", default=".")

    baseline_parser = subparsers.add_parser("baseline")
    baseline_parser.add_argument("path", nargs="?", default=".")
    baseline_parser.add_argument("--output", default="baseline.json")

    compare_parser = subparsers.add_parser("compare")
    compare_parser.add_argument("path", nargs="?", default=".")
    compare_parser.add_argument("--baseline", required=True)
    return parser


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()
    
    path = args.path
    if path == ".":
        # Check if the user actually provided a path or if it's just the default
        # If they just ran 'governance scan', we ask for the path
        import sys
        if len(sys.argv) < 3 or (len(sys.argv) == 3 and sys.argv[2] == "scan"):
             path = input("Please enter the path to the repository to analyze: ").strip()
             if not path:
                 print("Error: Path is required.")
                 return

    config = GovernanceConfig.from_env()
    engine = GovernanceEngine(config)
    result = engine.scan(path)
    if args.command == "scan":
        print(write_text_report(result))
        write_json_report(result, Path("governance-report.json"))
        write_html_report(result, Path("governance-report.html"))
        write_markdown_report(result, Path("governance-report.md"))
        write_junit_report(result, Path("governance-report.xml"))
        write_sarif_report(result, Path("governance-report.sarif"))
    elif args.command == "baseline":
        output_path = create_baseline(result, Path(args.output))
        print(output_path)
    elif args.command == "compare":
        changes = compare_baseline(result, Path(args.baseline))
        print("\n".join(changes))


if __name__ == "__main__":
    main()
