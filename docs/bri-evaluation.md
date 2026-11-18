# 🟪 BRI evaluation guide

For Build Release and Integration Engineering, use these checks to review answers about policies, workflow artifacts, and build evidence.

| Check | Question to score | Suggested evidence to save |
| --- | --- | --- |
| 🔎 Retrieval applicability | Does at least one retrieved excerpt give the requested fact for the correct product, version, and repository scope? | Query, candidate URLs, distinct article URLs, and exact excerpts |
| 🧾 Citation provenance | Does the quote occur in the excerpt attached to the cited source label? | Claim, label, quote, excerpt, and validator outcome |
| 🧠 Claim support | Does the passage establish the claim with all the stated conditions, units, and scope? | Reviewer judgment and a short explanation |

The agent automates quote matching. A reviewer checks applicability and whether the quote establishes the full claim.

## 📌 Example comparison

1. Use the same question for baseline retrieval and scoped retrieval with fallback.
2. Record whether each run retrieved an applicable excerpt and whether it answered or abstained.
3. Count a fact as supported only after reviewing the passage against the claim. Keep examples of wrong-scope sources and valid quotations that fail to support a claim.

The [live regression](live-regression.md) is one development example. Broader performance requires more independent questions and evidence.

<a id="claim-support-evaluation"></a>

## 🧪 Claim-support evaluation

Run the two checks on the curated fixtures from the repository root:

```powershell
.\.venv\Scripts\python.exe .\evaluate_claim_support.py
```

The runner recomputes the quote check and reports it alongside the documented human-readable support judgment and rationale. Each excerpt is a short controlled BRI example. The support judgments are fixture labels and can be audited in the [case file](../evaluation/claim_support_cases.json).

| Case | Expected quote check | Curated claim support |
| --- | --- | --- |
| ✅ Full support | Passed | Full |
| 🟡 Partial support | Passed | Partial |
| 🏷️ Wrong repository scope | Passed | Unsupported |
| 🔎 Irrelevant matching quote | Passed | Unsupported |
| ⬜ Missing evidence | Insufficient evidence | Insufficient |
| 🛑 Invented quote | Rejected | Unsupported |

All six quote-check outcomes matched their expected values in the recorded offline run. Three cases passed quote matching with partial or unsupported claims. These six fixtures demonstrate the distinction between the checks. Model accuracy would require testing model outputs against an independently reviewed dataset.

<a id="windows-verification"></a>

## 🪟 Windows verification

Anne ran both offline commands from a fresh GitHub checkout in Windows PowerShell on November 17, 2026, using her existing Python virtual environment. The results below come from her terminal output.

| Check | Observed result |
| --- | --- |
| 🧪 `python -m unittest discover -s tests -v` | 11 tests passed in 0.122 seconds. The suite includes the duplicate-retention regression and checks that different scopes, values, units, and qualifiers stay separate. |
| 🧾 `python evaluate_claim_support.py` | All 6 quote-check outcomes matched expectations. Of the 4 cases whose quotes matched, 1 supported the full claim, 1 supported part of the claim, and 2 provided insufficient support for the claim. |

The support statuses are curated for these fixtures. The runtime records one Windows test run. [Implementation commit](https://github.com/anne500/personal-web-research-agent/commit/1c4d99d8bd3f6c6362ca5c9a78b3db39e1fb73ec)
