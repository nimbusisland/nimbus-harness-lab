import importlib.util
import json
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MODULE = ROOT / "scripts" / "validate_public_projection.py"
POLICY = ROOT / "publication-policy.json"


def load_validator():
    spec = importlib.util.spec_from_file_location("validate_public_projection", MODULE)
    assert spec is not None
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


class PublicationGuardTests(unittest.TestCase):
    def setUp(self):
        self.validator = load_validator()
        self.policy = json.loads(POLICY.read_text(encoding="utf-8"))

    def test_activity_and_claim_routes_have_machine_readable_classes(self):
        findings = self.validator.validate_content_classes(ROOT, self.policy)
        self.assertEqual([], findings)

    def test_internal_paths_and_private_markers_are_rejected(self):
        findings = self.validator.scan_text(
            "<p>source /home/hermes/nimbus-research-log and api_key=secret</p>",
            self.policy,
            "progress/index.html",
        )
        self.assertIn("progress/index.html:forbidden:/home/hermes", findings)
        self.assertIn("progress/index.html:forbidden:api_key", findings)

    def test_public_github_registry_link_is_allowed(self):
        findings = self.validator.scan_text(
            "https://github.com/nimbusisland/nimbus-research-registry",
            self.policy,
            "progress/index.html",
        )
        self.assertEqual([], findings)

    def test_curator_paths_allow_content_but_reject_cname_and_workflows(self):
        allowed = self.validator.find_path_violations(
            ["progress/index.html", "assets/site.css", "sitemap.xml"], self.policy
        )
        denied = self.validator.find_path_violations(
            ["CNAME", ".github/workflows/pages.yml"], self.policy
        )
        self.assertEqual([], allowed)
        self.assertEqual([".github/workflows/pages.yml", "CNAME"], denied)

    def test_all_html_and_sitemap_parse(self):
        findings = self.validator.validate_static_site(ROOT)
        self.assertEqual([], findings)


if __name__ == "__main__":
    unittest.main()
