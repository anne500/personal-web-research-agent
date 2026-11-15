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
