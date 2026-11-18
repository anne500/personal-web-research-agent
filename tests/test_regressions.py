import contextlib
import io
import json
import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import Mock, patch

import research_agent as agent
from evaluate_claim_support import DEFAULT_CASES, evaluate_cases


DOCS = "https://docs.github.com"
REST = "/rest/actions/permissions"
CLOUD = (
    "/en/enterprise-cloud@latest/admin/enforcing-policies/"
    "enforcing-policies-for-your-enterprise/enforcing-policies-for-github-actions-in-your-enterprise"
)
REPO_SETTINGS = (
    "/en/enterprise-cloud@latest/repositories/managing-your-repositorys-settings-and-features/"
    "enabling-features-for-your-repository/managing-github-actions-settings-for-a-repository"
)
SERVER = "/en/enterprise-server%403.14/actions"
PUBLIC = "Public repositories support a range of 1 to 90 days."
PRIVATE = "Private and internal repositories support a range of 1 to 400 days."
QUESTION = "What are the configurable GitHub Actions artifact retention ranges on GitHub.com?"


def json_response(body):
    return Mock(**{"json.return_value": body})


def answer(source, quote=PUBLIC):
    return json.dumps({"claims": [{"claim": PUBLIC, "source": source, "quote": quote}]})


class RetrievalRegressionTests(unittest.TestCase):
    def test_duplicate_tavily_urls_trigger_official_fallback(self):
        duplicates = [
            f"{DOCS}/zh{REST}",
            f"{DOCS}/en{REST}#list-repositories-allowed-to-use-self-hosted-runners-in-an-organization",
            f"{DOCS}/en{REST}#get-artifact-and-log-retention-settings-for-a-repository",
        ]
        tavily = json_response({
            "results": [
                {"url": url, "raw_content": "REST permissions reference"}
                for url in [*duplicates, f"{DOCS}{SERVER}"]
            ]
        })
        github_search = json_response({
            "hits": [{"url": path} for path in [SERVER, CLOUD, REPO_SETTINGS]]
        })

        with (
            patch.dict(os.environ, {"TAVILY_API_KEY": "offline-test-key"}),
            patch.object(agent.requests, "post", return_value=tavily) as post,
            patch.object(agent.requests, "get", side_effect=[
                github_search,
                Mock(text=f"{PUBLIC}\n{PRIVATE}"),
                Mock(text=PUBLIC),
            ]) as get,
            contextlib.redirect_stdout(io.StringIO()) as output,
        ):
            sources = agent.search_sources(QUESTION, [], github_com=True)

        self.assertIn("Looking for additional articles in GitHub Docs", output.getvalue())
        self.assertEqual([item.url for item in sources], [f"{DOCS}/en{REST}", f"{DOCS}{CLOUD}", f"{DOCS}{REPO_SETTINGS}"])
        self.assertIn(PUBLIC, sources[1].excerpt)
        self.assertIn(PRIVATE, sources[1].excerpt)
        post.assert_called_once()
        self.assertEqual(post.call_args.args[0], agent.TAVILY_SEARCH)
        self.assertEqual(post.call_args.kwargs["json"]["include_domains"], ["docs.github.com"])
        self.assertEqual(get.call_args_list[0].kwargs["params"]["version"], "enterprise-cloud")
        self.assertEqual(
            [call.kwargs["params"]["pathname"] for call in get.call_args_list[1:]],
            [CLOUD, REPO_SETTINGS],
        )

    def test_enterprise_server_versions_and_lookalike_domain_are_excluded(self):
        for url in (
            f"{DOCS}{SERVER}",
            f"{DOCS}/en/enterprise-server@3.0/actions",
            f"{DOCS}/enterprise/2.22/admin",
            "https://docs.github.com.example.org/en/actions",
        ):
            with self.subTest(url=url):
                self.assertFalse(agent.is_github_com_docs_url(url))

        self.assertTrue(agent.is_github_com_docs_url(f"{DOCS}{CLOUD}"))
        self.assertTrue(agent.is_github_com_docs_url(f"{DOCS}/en/actions"))


class CitationRegressionTests(unittest.TestCase):
    def setUp(self):
        self.excerpts = {"[S1]": "The retention period is configurable.", "[S2]": PUBLIC}
        self.evidence = "\n\n".join(f"{label}\n{text}" for label, text in self.excerpts.items())

    def test_wrong_source_unknown_label_and_invented_quote_are_rejected(self):
        for label, quote in (("[S1]", PUBLIC), ("[S9]", PUBLIC), ("[S2]", "Up to 999 days.")):
            with self.subTest(label=label, quote=quote):
                with self.assertRaises(agent.CitationError):
                    agent.validate_claims(answer(label, quote), self.excerpts)

    def test_citation_retry_uses_same_excerpts(self):
        with (
            patch.object(agent, "query_ollama", side_effect=[answer("[S1]"), answer("[S2]")]) as model,
            contextlib.redirect_stdout(io.StringIO()) as output,
        ):
            digest = agent.generate_search_digest(QUESTION, self.evidence, self.excerpts)

        self.assertIn("Retrying with the same evidence", output.getvalue())
        self.assertIn(f"{PUBLIC} [S2]", digest)
        self.assertEqual(model.call_count, 2)
        self.assertEqual([call.args[1] for call in model.call_args_list], [self.evidence, self.evidence])

    def test_second_invalid_citation_withholds_claim(self):
        with (
            patch.object(agent, "query_ollama", return_value=answer("[S1]")) as model,
            contextlib.redirect_stdout(io.StringIO()),
        ):
            digest = agent.generate_search_digest(QUESTION, self.evidence, self.excerpts)

        self.assertEqual(model.call_count, 2)
        self.assertIn("Could not verify the answer's citations", digest)
        self.assertNotIn(PUBLIC, digest)

    def test_empty_claim_list_reports_insufficient_evidence(self):
        with patch.object(agent, "query_ollama", return_value='{"claims": []}') as model:
            digest = agent.generate_search_digest(QUESTION, self.evidence, self.excerpts)

        model.assert_called_once()
        self.assertIn("did not provide enough evidence", digest)

    def test_retention_findings_merge_with_all_source_quotes(self):
        excerpts = {
            "[S2]": f"{PUBLIC}\n{PRIVATE}",
            "[S3]": "For public repositories, choose from 1 to 90 days. "
                    "For private and internal repositories, choose from 1 to 400 days.",
        }
        response = json.dumps({"claims": [
            {"claim": PUBLIC, "source": "[S2]", "quote": PUBLIC},
            {"claim": PRIVATE, "source": "[S2]", "quote": PRIVATE},
            {"claim": PUBLIC.replace("1 to 90", "1–90").removesuffix("."), "source": "[S3]",
             "quote": "For public repositories, choose from 1 to 90 days."},
            {"claim": PRIVATE, "source": "[S3]",
             "quote": "For private and internal repositories, choose from 1 to 400 days."},
        ]})
        attempts = []
        with patch.object(agent, "query_ollama", return_value=response) as model:
            digest = agent.generate_search_digest(QUESTION, "saved excerpts", excerpts, citation_attempts=attempts)

        findings = [line for line in digest.splitlines() if line.startswith("- ")]
        self.assertEqual(findings, [f"- {PUBLIC} [S2] [S3]", f"- {PRIVATE} [S2] [S3]"])
        self.assertEqual(digest.count("  - Evidence [S"), 4)
        for claim in json.loads(response)["claims"]:
            self.assertIn(f"Evidence {claim['source']}: “{claim['quote']}”", digest)
        self.assertEqual(attempts, [{"response": response, "status": "passed"}])
        model.assert_called_once()

    def test_merge_preserves_distinct_scope_values_units_and_qualifiers(self):
        claims = [
            "Public repositories retain artifacts for up to 90 days.",
            "Private repositories retain artifacts for up to 90 days.",
            "Public repositories retain artifacts for up to 30 days.",
            "Public repositories retain artifacts for 90 days.",
            "Public repositories retain artifacts for up to 90 hours.",
        ]
        digest = agent.render_search_digest(
            [(claim, "[S1]", claim) for claim in claims] + [(claims[0], "[S1]", claims[0])]
        )
        self.assertEqual(sum(line.startswith("- ") for line in digest.splitlines()), len(claims))
        self.assertEqual(digest.count("Evidence:"), len(claims))


class EvidenceReplayTests(unittest.TestCase):
    def setUp(self):
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        original_directory = Path.cwd()
        os.chdir(directory.name)
        self.addCleanup(os.chdir, original_directory)

    def run_cli(self, *arguments):
        with (
            patch.object(sys, "argv", ["research_agent.py", *arguments]),
            contextlib.redirect_stdout(io.StringIO()) as output,
            contextlib.redirect_stderr(io.StringIO()) as errors,
        ):
            try:
                agent.main()
            except SystemExit as error:
                return error.code, errors.getvalue()
        return 0, output.getvalue()

    def test_saved_search_replays_success_rejection_and_insufficient_evidence(self):
        sources = [
            agent.SearchSource(f"{DOCS}/en/actions", "Configurable.", "search snippet"),
            agent.SearchSource(f"{DOCS}{CLOUD}", f"Retention details\n\n{PUBLIC}", "page excerpt"),
        ]
        for final_response, final_status in (
            (answer("[S2]"), "passed"),
            (answer("[S1]"), "rejected"),
            ('{"claims": []}', "insufficient_evidence"),
        ):
            with self.subTest(final_status=final_status):
                with (
                    patch.object(agent, "search_sources", return_value=sources),
                    patch.object(agent, "query_ollama", side_effect=[answer("[S1]"), final_response]),
                ):
                    status, output = self.run_cli("--search", QUESTION)
                self.assertEqual(status, 0, output)
                path = Path(next(line.removeprefix("Evidence: ") for line in output.splitlines()
                                 if line.startswith("Evidence: ")))
                saved = json.loads(path.read_text(encoding="utf-8"))
                self.assertEqual(saved["sources"]["[S2]"], vars(sources[1]))
                self.assertEqual(saved["citation_attempts"][0]["response"], answer("[S1]"))
                self.assertEqual(saved["citation_attempts"][1]["response"], final_response)
                digest = Path(path.name.removesuffix(".evidence.json") + ".md")
                self.assertIn(f"[Saved evidence]({path.name})", digest.read_text(encoding="utf-8"))

                with (
                    patch.object(agent.requests, "post", side_effect=AssertionError("Unexpected HTTP POST")),
                    patch.object(agent.requests, "get", side_effect=AssertionError("Unexpected HTTP GET")),
                ):
                    status, output = self.run_cli("--replay", str(path))
                    self.assertEqual(status, 0, output)
                    self.assertIn("Attempt 1: rejected", output)
                    self.assertIn(f"Attempt 2: {final_status}", output)
                    self.assertIn("All outcomes matched", output)

                    saved["sources"]["[S1]"]["excerpt"] = PUBLIC
                    path.write_text(json.dumps(saved), encoding="utf-8")
                    status, error = self.run_cli("--replay", str(path))
                    self.assertEqual(status, 1)
                    self.assertIn("differs from the recorded outcome", error)

    def test_direct_url_saves_exact_excerpt_for_review(self):
        url = f"{DOCS}/en/actions"
        excerpt = f"Retention details\n\n{PUBLIC}"
        with (
            patch.object(agent, "fetch_source", return_value=(url, excerpt)),
            patch.object(agent, "generate_digest", return_value=PUBLIC),
        ):
            status, output = self.run_cli("--url", url, QUESTION)
        self.assertEqual(status, 0, output)
        path, = Path.cwd().glob("digest-*.evidence.json")
        saved = json.loads(path.read_text(encoding="utf-8"))
        self.assertEqual(saved["sources"]["[S1]"]["excerpt"], excerpt)
        self.assertEqual(saved["sources"]["[S1]"]["url"], url)
        self.assertEqual(saved["citation_attempts"], [])
        status, output = self.run_cli("--replay", str(path))
        self.assertEqual(status, 0, output)
        self.assertIn("Citation replay is available for search runs", output)


class ClaimSupportEvaluationTests(unittest.TestCase):
    def test_quote_matching_and_curated_support_are_reported_independently(self):
        cases = json.loads(DEFAULT_CASES.read_text(encoding="utf-8"))
        with (
            patch.object(agent.requests, "post", side_effect=AssertionError("Unexpected HTTP POST")),
            patch.object(agent.requests, "get", side_effect=AssertionError("Unexpected HTTP GET")),
        ):
            results = evaluate_cases(cases)

        self.assertTrue(all(row["quote_status"] == row["expected_quote_status"] for row in results))
        self.assertEqual(
            {row["case"]: (row["quote_status"], row["reviewed_support"]) for row in results},
            {
                "full-support": ("passed", "full"),
                "partial-support": ("passed", "partial"),
                "wrong-scope": ("passed", "unsupported"),
                "irrelevant-matching-quote": ("passed", "unsupported"),
                "missing-evidence": ("insufficient_evidence", "insufficient"),
                "invented-quote": ("rejected", "unsupported"),
            },
        )
