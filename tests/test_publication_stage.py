import json
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path

SOURCE_ROOT = Path(__file__).resolve().parents[1]
STAGE_SCRIPT = SOURCE_ROOT / "scripts" / "publication_stage.py"


def run(*args, cwd):
    return subprocess.run(args, cwd=cwd, text=True, capture_output=True)


class PublicationStageIntegrationTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        base = Path(self.tmp.name)
        self.repo = base / "site"
        self.state = base / "state"
        self.repo.mkdir()
        run("git", "init", "-q", cwd=self.repo)
        run("git", "config", "user.email", "test@example.invalid", cwd=self.repo)
        run("git", "config", "user.name", "Test", cwd=self.repo)
        (self.repo / "scripts").mkdir()
        shutil.copy(SOURCE_ROOT / "scripts" / "validate_public_projection.py", self.repo / "scripts")
        shutil.copy(SOURCE_ROOT / "publication-policy.json", self.repo)
        for rel, body in {
            "index.html": '<html><body><h1>Home</h1></body></html>',
            "research/index.html": '<html><body data-content-class="activity"><h1>Research</h1></body></html>',
            "progress/index.html": '<html><body data-content-class="activity"><h1>Progress</h1></body></html>',
            "papers/index.html": '<html><body data-content-class="source-note"><h1>Papers</h1></body></html>',
            "simulations/index.html": '<html><body data-content-class="validity-claim" data-validity-status="HOLD"><h1>Claims</h1></body></html>',
        }.items():
            path = self.repo / rel
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(body, encoding="utf-8")
        (self.repo / "sitemap.xml").write_text('<?xml version="1.0"?><urlset/>', encoding="utf-8")
        run("git", "add", ".", cwd=self.repo)
        self.assertEqual(0, run("git", "commit", "-qm", "base", cwd=self.repo).returncode)

    def tearDown(self):
        self.tmp.cleanup()

    def invoke(self, command, run_id="run-001"):
        return run(
            "python3",
            str(STAGE_SCRIPT),
            "--repo",
            str(self.repo),
            "--state-root",
            str(self.state),
            command,
            "--run-id",
            run_id,
            cwd=self.repo,
        )

    def test_valid_stage_exports_patch_and_removes_worktree(self):
        init = self.invoke("init")
        self.assertEqual(0, init.returncode, init.stderr + init.stdout)
        stage = Path(json.loads(init.stdout)["stage"])
        progress = stage / "progress" / "index.html"
        progress.write_text(progress.read_text(encoding="utf-8").replace("Progress", "Current activity"), encoding="utf-8")
        final = self.invoke("finalize")
        self.assertEqual(0, final.returncode, final.stderr + final.stdout)
        payload = json.loads(final.stdout)
        self.assertTrue(Path(payload["patch"]).exists())
        self.assertTrue(Path(payload["manifest"]).exists())
        self.assertFalse(stage.exists())

    def test_disallowed_stage_change_is_rejected_and_preserved(self):
        init = self.invoke("init", "run-002")
        self.assertEqual(0, init.returncode)
        stage = Path(json.loads(init.stdout)["stage"])
        (stage / "CNAME").write_text("evil.example\n", encoding="utf-8")
        final = self.invoke("finalize", "run-002")
        self.assertEqual(2, final.returncode)
        payload = json.loads(final.stdout)
        self.assertFalse(payload["valid"])
        self.assertTrue(stage.exists())

    def test_run_id_rejects_path_traversal(self):
        result = self.invoke("init", "../escape")
        self.assertEqual(2, result.returncode)


if __name__ == "__main__":
    unittest.main()
