#!/usr/bin/env python3
"""Validate Nimbus's public-site projection before any publication step."""

from __future__ import annotations

import argparse
import fnmatch
import json
import re
import subprocess
import xml.etree.ElementTree as ET
from html.parser import HTMLParser
from pathlib import Path
from typing import Iterable


class StructureParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.h1_count = 0

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag.lower() == "h1":
            self.h1_count += 1


def load_policy(path: Path) -> dict:
    data = json.loads(path.read_text(encoding="utf-8"))
    if data.get("schema_version") != 1:
        raise ValueError(f"unsupported policy schema: {path}")
    return data


def matches(path: str, patterns: Iterable[str]) -> bool:
    return any(fnmatch.fnmatchcase(path, pattern) for pattern in patterns)


def find_path_violations(paths: Iterable[str], policy: dict) -> list[str]:
    allowed = policy.get("curator_allow", [])
    forbidden = policy.get("curator_forbid", [])
    return sorted(
        {
            path
            for path in paths
            if matches(path, forbidden) or not matches(path, allowed)
        }
    )


def scan_text(text: str, policy: dict, path: str) -> list[str]:
    lowered = text.lower()
    return [
        f"{path}:forbidden:{marker}"
        for marker in policy.get("forbidden_text", [])
        if marker.lower() in lowered
    ]


def validate_content_classes(root: Path, policy: dict) -> list[str]:
    findings: list[str] = []
    classes = policy.get("content_classes", {})
    for content_class in ("activity", "source-note"):
        for rel in classes.get(content_class, []):
            text = (root / rel).read_text(encoding="utf-8")
            pattern = rf'<body[^>]*data-content-class=["\']{re.escape(content_class)}["\']'
            if not re.search(pattern, text, re.I):
                findings.append(f"{rel}:missing-content-class:{content_class}")
    for rel, status in classes.get("validity-claim", {}).items():
        text = (root / rel).read_text(encoding="utf-8")
        if not re.search(r'<body[^>]*data-content-class=["\']validity-claim["\']', text, re.I):
            findings.append(f"{rel}:missing-content-class:validity-claim")
        status_pattern = rf'data-validity-status=["\']{re.escape(status)}["\']'
        if not re.search(status_pattern, text, re.I):
            findings.append(f"{rel}:missing-validity-status:{status}")
    return sorted(findings)


def validate_static_site(root: Path) -> list[str]:
    findings: list[str] = []
    for path in sorted(root.glob("**/*.html")):
        if ".git" in path.parts:
            continue
        rel = path.relative_to(root).as_posix()
        parser = StructureParser()
        try:
            parser.feed(path.read_text(encoding="utf-8"))
            parser.close()
        except Exception as exc:  # HTMLParser failures are structural blockers.
            findings.append(f"{rel}:html-parse:{exc}")
            continue
        if parser.h1_count != 1:
            findings.append(f"{rel}:h1-count:{parser.h1_count}")
    try:
        ET.parse(root / "sitemap.xml")
    except Exception as exc:
        findings.append(f"sitemap.xml:xml-parse:{exc}")
    return findings


def changed_paths(root: Path) -> list[str]:
    commands = [
        ["git", "diff", "HEAD", "--name-only", "--diff-filter=ACMRD"],
        ["git", "ls-files", "--others", "--exclude-standard"],
    ]
    paths: list[str] = []
    for command in commands:
        result = subprocess.run(command, cwd=root, text=True, capture_output=True, check=True)
        paths.extend(line for line in result.stdout.splitlines() if line)
    return sorted(set(paths))


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", default=".")
    parser.add_argument("--policy", default="publication-policy.json")
    parser.add_argument("--scope", choices=["changed", "all"], default="changed")
    return parser


def main() -> int:
    args = build_parser().parse_args()
    root = Path(args.root).resolve()
    policy_path = Path(args.policy)
    if not policy_path.is_absolute():
        policy_path = root / policy_path
    policy = load_policy(policy_path)
    paths = changed_paths(root) if args.scope == "changed" else []
    findings = find_path_violations(paths, policy) if paths else []
    findings += validate_content_classes(root, policy)
    findings += validate_static_site(root)
    scan_paths = [root / p for p in paths if (root / p).is_file()] if paths else list(root.glob("**/*.html"))
    for path in scan_paths:
        if ".git" in path.parts:
            continue
        rel = path.relative_to(root).as_posix()
        try:
            findings += scan_text(path.read_text(encoding="utf-8"), policy, rel)
        except UnicodeDecodeError:
            continue
    findings = sorted(set(findings))
    result = {
        "mode": policy.get("mode"),
        "scope": args.scope,
        "changed_paths": paths,
        "findings": findings,
        "valid": not findings,
        "publish_allowed": policy.get("mode") == "live" and not findings,
    }
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if not findings else 2


if __name__ == "__main__":
    raise SystemExit(main())
