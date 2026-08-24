#!/usr/bin/env python3
"""Create and finalize isolated dry-run worktrees for Nimbus site projection."""

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
        "mode": "dry-run",
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
        payload = {
            "run_id": run_id,
            "stage": str(stage),
            "valid": False,
            "findings": validation_payload.get("findings", []),
            "preserved_for_inspection": True,
        }
        return 2, payload

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
    manifest_payload = {
        "schema_version": 1,
        "run_id": run_id,
        "mode": "dry-run",
        "base_head": run(stage, "git", "rev-parse", "HEAD").stdout.strip(),
        "changed_paths": changed,
        "validation": validation_payload,
        "publish_authorized": False,
    }
    manifest.write_text(json.dumps(manifest_payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    removal = run(repo, "git", "worktree", "remove", "--force", str(stage), check=False)
    if removal.returncode != 0:
        raise RuntimeError(removal.stderr.strip() or "git worktree remove failed")
    return 0, {
        "run_id": run_id,
        "valid": True,
        "mode": "dry-run",
        "patch": str(patch),
        "manifest": str(manifest),
        "changed_paths": changed,
        "publish_authorized": False,
    }


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo", default=".")
    parser.add_argument("--state-root", default=str(Path.home() / ".local/state/nimbus/publication-staging"))
    sub = parser.add_subparsers(dest="command", required=True)
    for name in ("init", "finalize"):
        command = sub.add_parser(name)
        command.add_argument("--run-id", required=True)
    return parser


def main() -> int:
    args = build_parser().parse_args()
    repo = Path(args.repo).resolve()
    state_root = Path(args.state_root).expanduser().resolve()
    try:
        if args.command == "init":
            payload = init_stage(repo, state_root, args.run_id)
            code = 0
        else:
            code, payload = finalize_stage(repo, state_root, args.run_id)
    except (ValueError, RuntimeError) as exc:
        print(json.dumps({"valid": False, "error": str(exc)}, ensure_ascii=False, indent=2))
        return 2
    print(json.dumps(payload, ensure_ascii=False, indent=2))
    return code


if __name__ == "__main__":
    raise SystemExit(main())
