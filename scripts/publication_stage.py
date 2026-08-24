#!/usr/bin/env python3
"""Stage, validate, and publish gated Nimbus research-site projections."""

from __future__ import annotations

import argparse
import json
import re
import subprocess
from pathlib import Path

RUN_ID_RE = re.compile(r"[A-Za-z0-9][A-Za-z0-9._-]{0,63}\Z")


def run(cwd: Path, *args: str, check: bool = True) -> subprocess.CompletedProcess[str]:
    return subprocess.run(list(args), cwd=cwd, text=True, capture_output=True, check=check)


def validate_run_id(run_id: str) -> None:
    if not RUN_ID_RE.fullmatch(run_id) or ".." in run_id:
        raise ValueError("run_id must be 1-64 safe filename characters without '..'")


def stage_paths(state_root: Path, run_id: str) -> tuple[Path, Path, Path]:
    run_root = state_root / run_id
    return run_root / "worktree", run_root / "projection.patch", run_root / "manifest.json"


def init_stage(repo: Path, state_root: Path, run_id: str) -> dict:
    validate_run_id(run_id)
    if run(repo, "git", "status", "--porcelain").stdout.strip():
        raise RuntimeError("site repository is not clean; refusing staging worktree")
    if run(repo, "git", "branch", "--show-current").stdout.strip() != "gh-pages":
        raise RuntimeError("site repository must be on gh-pages")
    stage, patch, manifest = stage_paths(state_root, run_id)
    if stage.exists() or patch.exists() or manifest.exists():
        raise RuntimeError(f"run_id already exists: {run_id}")
    stage.parent.mkdir(parents=True, exist_ok=True)
    result = run(repo, "git", "worktree", "add", "--detach", str(stage), "HEAD", check=False)
    if result.returncode != 0:
        raise RuntimeError(result.stderr.strip() or "git worktree add failed")
    return {
        "run_id": run_id,
        "stage": str(stage),
        "base_head": run(repo, "git", "rev-parse", "HEAD").stdout.strip(),
        "mode": "isolated-stage",
    }


def finalize_stage(repo: Path, state_root: Path, run_id: str) -> tuple[int, dict]:
    validate_run_id(run_id)
    stage, patch, manifest = stage_paths(state_root, run_id)
    if not stage.exists():
        raise RuntimeError(f"stage not found: {stage}")
    validator = stage / "scripts" / "validate_public_projection.py"
    validation = run(stage, "python3", str(validator), "--scope", "changed", check=False)
    try:
        validation_payload = json.loads(validation.stdout)
    except json.JSONDecodeError as exc:
        raise RuntimeError(f"validator did not return JSON: {exc}") from exc
    if validation.returncode != 0:
        return 2, {
            "run_id": run_id,
            "stage": str(stage),
            "valid": False,
            "findings": validation_payload.get("findings", []),
            "preserved_for_inspection": True,
        }
    changed = validation_payload.get("changed_paths", [])
    if not changed:
        return 3, {
            "run_id": run_id,
            "stage": str(stage),
            "valid": True,
            "reason": "no_changes",
            "preserved_for_inspection": True,
        }
    untracked = [
        line
        for line in run(stage, "git", "ls-files", "--others", "--exclude-standard").stdout.splitlines()
        if line
    ]
    if untracked:
        run(stage, "git", "add", "-N", "--", *untracked)
    patch_text = run(stage, "git", "diff", "--binary", "HEAD").stdout
    if not patch_text:
        raise RuntimeError("validated changes produced an empty patch")
    patch.write_text(patch_text, encoding="utf-8")
    publish_authorized = bool(validation_payload.get("publish_allowed"))
    manifest_payload = {
        "schema_version": 1,
        "run_id": run_id,
        "mode": validation_payload.get("mode"),
        "base_head": run(stage, "git", "rev-parse", "HEAD").stdout.strip(),
        "changed_paths": changed,
        "validation": validation_payload,
        "publish_authorized": publish_authorized,
        "published": False,
    }
    manifest.write_text(json.dumps(manifest_payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    removal = run(repo, "git", "worktree", "remove", "--force", str(stage), check=False)
    if removal.returncode != 0:
        raise RuntimeError(removal.stderr.strip() or "git worktree remove failed")
    return 0, {
        "run_id": run_id,
        "valid": True,
        "mode": validation_payload.get("mode"),
        "patch": str(patch),
        "manifest": str(manifest),
        "changed_paths": changed,
        "publish_authorized": publish_authorized,
    }


def publish_stage(repo: Path, state_root: Path, run_id: str, message: str) -> tuple[int, dict]:
    validate_run_id(run_id)
    _stage, patch, manifest = stage_paths(state_root, run_id)
    if not patch.is_file() or not manifest.is_file():
        raise RuntimeError("validated patch or manifest is missing")
    data = json.loads(manifest.read_text(encoding="utf-8"))
    if not data.get("publish_authorized"):
        raise RuntimeError("manifest is not authorized for publication")
    if data.get("published"):
        raise RuntimeError("manifest has already been published")
    if not message.strip():
        raise RuntimeError("publish message must not be empty")
    if run(repo, "git", "status", "--porcelain").stdout.strip():
        raise RuntimeError("site repository is not clean")
    branch = run(repo, "git", "branch", "--show-current").stdout.strip()
    if branch != "gh-pages":
        raise RuntimeError(f"wrong branch: expected gh-pages, got {branch or 'detached'}")
    current = run(repo, "git", "rev-parse", "HEAD").stdout.strip()
    if current != data.get("base_head"):
        raise RuntimeError("base HEAD changed after validation; refusing publication")
    fetch = run(repo, "git", "fetch", "--quiet", "origin", "gh-pages", check=False)
    if fetch.returncode != 0:
        raise RuntimeError(fetch.stderr.strip() or "origin fetch failed")
    remote = run(repo, "git", "rev-parse", "origin/gh-pages").stdout.strip()
    if remote != current:
        raise RuntimeError("origin/gh-pages changed after staging; refusing publication")
    checked = run(repo, "git", "apply", "--check", str(patch), check=False)
    if checked.returncode != 0:
        raise RuntimeError(checked.stderr.strip() or "validated patch no longer applies")
    applied = run(repo, "git", "apply", str(patch), check=False)
    if applied.returncode != 0:
        raise RuntimeError(applied.stderr.strip() or "patch apply failed")
    validator = repo / "scripts" / "validate_public_projection.py"
    validation = run(repo, "python3", str(validator), "--scope", "changed", check=False)
    try:
        validation_payload = json.loads(validation.stdout)
    except json.JSONDecodeError as exc:
        run(repo, "git", "reset", "--hard", "HEAD")
        raise RuntimeError(f"post-apply validator did not return JSON: {exc}") from exc
    changed = validation_payload.get("changed_paths", [])
    if validation.returncode != 0 or sorted(changed) != sorted(data.get("changed_paths", [])):
        run(repo, "git", "reset", "--hard", "HEAD")
        raise RuntimeError("post-apply validation or changed-path set failed")
    run(repo, "git", "add", "--", *changed)
    committed = run(repo, "git", "commit", "-m", message, check=False)
    if committed.returncode != 0:
        run(repo, "git", "reset", "--hard", "HEAD")
        raise RuntimeError(committed.stderr.strip() or "site commit failed")
    commit = run(repo, "git", "rev-parse", "HEAD").stdout.strip()
    pushed = run(repo, "git", "push", "--porcelain", "origin", "HEAD:gh-pages", check=False)
    if pushed.returncode != 0:
        raise RuntimeError(pushed.stderr.strip() or "site push failed")
    data["published"] = True
    data["published_commit"] = commit
    manifest.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return 0, {
        "run_id": run_id,
        "published": True,
        "commit": commit,
        "changed_paths": changed,
        "remote": "origin/gh-pages",
    }


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo", default=".")
    parser.add_argument("--state-root", default=str(Path.home() / ".local/state/nimbus/publication-staging"))
    sub = parser.add_subparsers(dest="command", required=True)
    for name in ("init", "finalize"):
        command = sub.add_parser(name)
        command.add_argument("--run-id", required=True)
    publish = sub.add_parser("publish")
    publish.add_argument("--run-id", required=True)
    publish.add_argument("--message", required=True)
    return parser


def main() -> int:
    args = build_parser().parse_args()
    repo = Path(args.repo).resolve()
    state_root = Path(args.state_root).expanduser().resolve()
    try:
        if args.command == "init":
            payload = init_stage(repo, state_root, args.run_id)
            code = 0
        elif args.command == "finalize":
            code, payload = finalize_stage(repo, state_root, args.run_id)
        else:
            code, payload = publish_stage(repo, state_root, args.run_id, args.message)
    except (ValueError, RuntimeError, json.JSONDecodeError) as exc:
        print(json.dumps({"valid": False, "error": str(exc)}, ensure_ascii=False, indent=2))
        return 2
    print(json.dumps(payload, ensure_ascii=False, indent=2))
    return code


if __name__ == "__main__":
    raise SystemExit(main())
