"""Plot curated support for the fixtures that pass automated quote matching."""

from collections import Counter
import json
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt

from evaluate_claim_support import DEFAULT_CASES, evaluate_cases


def main():
    cases = json.loads(DEFAULT_CASES.read_text(encoding="utf-8"))
    results = evaluate_cases(cases)
    matched = [row for row in results if row["quote_status"] == "passed"]
    support_counts = Counter(row["reviewed_support"] for row in matched)
    groups = [
        ("full", "Full support", "#15803D"),
        ("partial", "Partial support", "#A16207"),
        ("unsupported", "Unsupported", "#B91C1C"),
    ]
    values = [support_counts[key] for key, _, _ in groups]
    output = Path(__file__).resolve().parents[1] / "docs" / "assets" / "claim-support-results.svg"

    with matplotlib.rc_context({
        "svg.fonttype": "none",
        "svg.hashsalt": "project8-claim-support",
        "font.family": "DejaVu Sans",
        "font.size": 11,
        "text.color": "#0F172A",
        "axes.labelcolor": "#334155",
        "xtick.color": "#334155",
        "ytick.color": "#0F172A",
    }):
        fig, ax = plt.subplots(figsize=(10.5, 3.8))
        fig.subplots_adjust(left=0.22, right=0.93, top=0.68, bottom=0.29)
        fig.text(0.07, 0.89, "Claim support after quote matching", fontsize=23, fontweight="bold")
        fig.text(0.07, 0.78, f"{len(matched)} of {len(results)} controlled fixtures passed automated quote matching.",
                 fontsize=12, color="#475569")
        ax.barh([name for _, name, _ in groups], values, color=[color for _, _, color in groups],
                height=0.49, zorder=2)
        ax.invert_yaxis()
        ax.set_xlim(0, max(values) + 0.5)
        ax.set_xticks(range(max(values) + 1))
        ax.set_xlabel("Number of matching-quote fixtures")
        ax.grid(axis="x", color="#CBD5E1", linewidth=0.8)
        ax.tick_params(axis="y", length=0, pad=10)
        ax.spines[["top", "right", "left"]].set_visible(False)
        ax.spines["bottom"].set_color("#94A3B8")
        for index, value in enumerate(values):
            ax.text(value + 0.06, index, str(value), va="center", fontweight="bold")

        fig.text(0.07, 0.11, "Support labels are curated judgments for the recorded fixtures.",
                 fontsize=10, color="#475569")
        fig.text(0.07, 0.055, "Source: evaluation/claim_support_cases.json", fontsize=10, color="#475569")
        fig.savefig(output, metadata={
            "Title": "Claim support after quote matching",
            "Description": "Counts of curated claim support among controlled fixtures that matched their quote.",
            "Date": None,
        })
        plt.close(fig)


if __name__ == "__main__":
    main()
