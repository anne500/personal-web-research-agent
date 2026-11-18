"""Replay citation checks and report curated claim-support judgments."""

import argparse
import json
from pathlib import Path

from research_agent import check_citations


DEFAULT_CASES = Path(__file__).resolve().parent / "evaluation" / "claim_support_cases.json"


def evaluate_cases(cases):
    results = []
    for case in cases:
        outcome, _ = check_citations(json.dumps({"claims": case["claims"]}), case["excerpts"])
        results.append({
            "case": case["id"],
            "quote_status": outcome["status"],
            "expected_quote_status": case["expected_quote_status"],
            "reviewed_support": case["review"]["support"],
            "review_reason": case["review"]["reason"],
        })
    return results


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--cases", type=Path, default=DEFAULT_CASES, help="Path to the offline JSON cases")
    args = parser.parse_args()
    try:
        cases = json.loads(args.cases.read_text(encoding="utf-8"))
        if not isinstance(cases, list) or not cases:
            raise ValueError("Provide a nonempty list of evaluation cases.")
        results = evaluate_cases(cases)
    except (OSError, ValueError, KeyError, TypeError) as error:
        parser.exit(1, f"Could not evaluate cases: {error}\n")

    print("| Case | Quote check | Expected quote check | Curated claim support | Review reason |")
    print("| --- | --- | --- | --- | --- |")
    for row in results:
        print("| " + " | ".join(str(value).replace("|", r"\|").replace("\n", " ")
                                 for value in row.values()) + " |")
    matches = sum(row["quote_status"] == row["expected_quote_status"] for row in results)
    print(f"\nQuote-check expectations matched: {matches}/{len(results)}")
    print("Claim-support labels are curated review judgments.")
    return 0 if matches == len(results) else 1


if __name__ == "__main__":
    raise SystemExit(main())
