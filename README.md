# 🔎 Personal Web Research Agent

A Python research agent that retrieves web evidence, runs Qwen locally through Ollama, and writes a timestamped Markdown digest. It demonstrates how to recover when search returns three URLs for a single article and how to check the quotes behind an answer.

<a id="-tutorial-baseline"></a>

<a id="base-tutorial"></a>

## 🟦 Base tutorial

Darsh Shah’s tutorial takes a research question from the terminal, searches the web through Ollama, and retrieves the top five pages. It uses Requests and BeautifulSoup to extract page text, then sends the text to local Qwen through Ollama and saves a timestamped Markdown digest. This project retains that question-to-digest workflow. [Darsh Shah’s freeCodeCamp tutorial: How to Build a Personal Web Research AI Agent with Ollama and Qwen](https://www.freecodecamp.org/news/build-a-personal-ai-web-research-agent-with-ollama-and-qwen/)

<a id="-project-extensions-and-contributions"></a>

## 🧩 Extensions added in Project 8

### Implemented extensions

- [x] **1. Save and replay evidence.** [Offline round-trip tests](tests/test_regressions.py)

### Baseline and contribution table

| Origin | Item | Scope or contribution | Verification |
| --- | --- | --- | --- |
| 🟦 Tutorial baseline | [Base tutorial](#base-tutorial) | Ollama web search, webpage text extraction, local Qwen summarization, and a timestamped Markdown digest. | See the [tutorial baseline](#base-tutorial). |
| 🛠️ Adaptation | 🔗 Direct URL research (adaptation) | Added `--url` to analyze a supplied page with local Qwen without a Tavily key. | Live dependency-caching question and offline URL excerpt test |
| 🛠️ Adaptation | 🌐 Tavily web search (adaptation) | Replaced Ollama web search with Tavily, with optional domain filtering and up to three excerpts or snippets. | Live retention regression |
| 🧩 Extension | 🏷️ Product and version scope | `--github-com` keeps GitHub.com and Enterprise Cloud documentation and excludes versioned Enterprise Server pages. | Live scoped search and offline URL tests |
| 🧩 Extension | 🔁 Article deduplication and fallback | In `--github-com` mode, groups locale and fragment variants of an article. GitHub Docs search can supplement the evidence when fewer than three distinct sources remain. | Live fallback and offline retrieval regression |
| 🧩 Extension | 🧾 Citation validation | In search mode, checks that each quoted passage appears in its cited excerpt, allowing whitespace differences. | Live digest and offline wrong-source, unknown-label, and invented-quote cases |
| 🧩 Extension | 🛑 Retry and abstention | Retries invalid citations once with the same evidence, then withholds claims if validation still fails. Reports insufficient evidence when the model produces no claims. | Offline retry and abstention cases, plus a live insufficient-evidence run |
| 🧩 Extension | 💾 Save and replay evidence | Saves source URLs, labels, exact excerpts, model responses, and citation outcomes. Replays each search attempt against the stored evidence. | [Offline tests](tests/test_regressions.py) cover accepted and rejected citations and insufficient evidence with HTTP calls disabled. |
| 🟠 Planned extension | **2. Merge repeated findings** | Merge duplicate claims while preserving all supporting quotes and source labels. | [Completion criteria](#planned-extensions) |
| 🟠 Planned extension | **3. Claim-support evaluation set** | Score factual support independently of quote matching. | [Completion criteria](#planned-extensions) |

The live retention regression shows what the added retrieval and citation controls changed for one GitHub.com policy question. The BRI evaluation guide explains how to assess source applicability, quote matching, and claim support as separate checks. [Live regression](docs/live-regression.md) · [BRI evaluation guide](docs/bri-evaluation.md)

### Planned extensions

Move each verified extension to Implemented extensions and link its test or verification result.

- [ ] **2. Merge repeated findings.** Show a repeated finding once and preserve every supporting source and quote. **Complete when** the [retention regression](docs/live-regression.md) produces one public finding and one private/internal finding, each retaining its verified citations, and a test confirms that distinct scopes stay separate.
- [ ] **3. Add a claim-support evaluation set.** Include examples of fully supported claims, partly supported claims, wrong repository scopes, missing evidence, and quotations that appear in the excerpt but fail to establish the claim. **Complete when** an offline evaluation records quote matching and claim support separately against documented expected results.

<a id="explore-the-project"></a>

## 🧭 Explore the project

[🧩 Architecture](#architecture) · [🚀 Setup](#setup) · [🧪 Results & verification](#verification) · [🗂️ Evidence & guides](docs/bri-evaluation.md) · [📚 Tutorial credit](#tutorial-credit) · [🎨 Visual standard](https://github.com/anne500/multi-agent-study-guide/blob/main/VISUAL_STYLE.md#readme-presentation-standard)

<a id="architecture"></a>

## 🧩 Architecture

```mermaid
flowchart TD
    Q["Research question"] --> M{"Input mode"}
    M -->|"--url"| U["Fetch supplied page"]
    M -->|"--search"| T["Tavily search"]
    T -->|"--github-com"| F["Filter scope and group article URLs"]
    F -->|"Fewer than three articles"| G["GitHub Docs API fallback"]
    F -->|"Three distinct articles"| E["Select evidence excerpts"]
    G --> E
    T -->|"General search"| E
    U --> E
    E --> O["Local Qwen via Ollama"]
    O -->|"Search mode"| V{"Quote and label match"}
    V -->|"Pass"| D["Markdown digest"]
    V -->|"First failure"| O
    V -->|"Second failure"| A["Digest with validation failure"]
    O -->|"URL mode"| D
    classDef input fill:#dbeafe,stroke:#1d4ed8,color:#172554;
    classDef retrieval fill:#ccfbf1,stroke:#0f766e,color:#134e4a;
    classDef model fill:#ede9fe,stroke:#7c3aed,color:#2e1065;
    classDef check fill:#fef3c7,stroke:#b45309,color:#451a03;
    classDef output fill:#dcfce7,stroke:#15803d,color:#14532d;
    classDef failure fill:#fee2e2,stroke:#b91c1c,color:#450a0a;
    class Q,M input;
    class T,U,F,G,E retrieval;
    class O model;
    class V check;
    class D output;
    class A failure;
```

<a id="setup"></a>

## 🚀 Run on Windows

Prerequisites are Python 3.10+ and [Ollama](https://ollama.com/download). Run these commands from the repository directory in PowerShell. Start Ollama before generating a digest.

```powershell
py -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
ollama pull qwen3.5:4b
```

### 🔗 Research a supplied page

```powershell
.\.venv\Scripts\python.exe .\research_agent.py `
    --url "https://docs.github.com/en/actions/how-tos/manage-workflow-runs/download-workflow-artifacts" `
    "How long does GitHub retain workflow artifacts by default?"
```

### 🔍 Search with GitHub.com scope

Create a key in the [Tavily dashboard](https://app.tavily.com/). The example reads it with a masked prompt and clears it from the PowerShell session afterward. Search sends the question to Tavily and may also send it to GitHub Docs in scoped mode. Qwen generation runs on your machine.

```powershell
$tavilyKey = Read-Host "Paste your Tavily API key" -AsSecureString
try {
    $env:TAVILY_API_KEY = [pscredential]::new("tavily", $tavilyKey).GetNetworkCredential().Password

    .\.venv\Scripts\python.exe .\research_agent.py `
        --search --github-com `
        "On GitHub.com, what are the configurable GitHub Actions artifact retention ranges for public repositories and for private and internal repositories?"
}
finally {
    Remove-Item Env:TAVILY_API_KEY -ErrorAction SilentlyContinue
    Remove-Variable tavilyKey
}
```

Use `--search --domain example.org` for a different domain. The agent writes `digest-*.md` in the current directory.

### 🔁 Replay citation checks from a saved search

Each new digest links to its companion `digest-*.evidence.json` file. After a search run, copy the path printed on its `Evidence:` line and use it in this command:

```powershell
.\.venv\Scripts\python.exe .\research_agent.py --replay "path\to\digest.evidence.json"
```

Replay reads the saved excerpts and model replies, reruns citation validation for each attempt, and exits successfully when the original outcomes match. A recorded rejection can replay successfully. Replay runs offline and checks quote matching. Factual support still requires reviewing the claim against its evidence. Direct URL runs save the selected excerpt for review, while search runs also record structured citation attempts.

<a id="verification"></a>

## 🧪 Verify offline

After installing the Python dependencies, run the tests without credentials, network calls, or a local model:

```powershell
.\.venv\Scripts\python.exe -m unittest discover -s tests -v
```

| Live case | Before the fallback | With the fallback |
| --- | --- | --- |
| GitHub.com artifact retention ranges | Three URLs pointed to one REST article. The agent reported insufficient evidence. | The GitHub Docs API supplied Enterprise Cloud excerpts with the applicable ranges. The quotes passed validation. |

See the [recorded live regression](docs/live-regression.md) and [BRI evaluation guide](docs/bri-evaluation.md).

<a id="tutorial-credit"></a>

## 🙌 Acknowledgment

Thanks to Darsh Shah for the freeCodeCamp tutorial that provided the starting workflow.
