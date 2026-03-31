#!/usr/bin/env python3
"""
CI orchestrator: detect new Spring Boot minor versions, generate skills,
and output release info for GitHub Actions.

versions.json tracks minor versions (e.g. "3.4", "4.0") with the latest
known patch used for doc fetching. Skills are labeled as "X.Y.x" since
patch releases don't add new features.
"""

from __future__ import annotations

import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
import zipfile
from pathlib import Path

import httpx

VERSIONS_FILE = Path("versions.json")
SCRIPT_FILE = Path("generate_skill.py")
OUTPUT_DIR = Path("output")
ZIPS_DIR = Path("zips")
GITHUB_OUTPUT = os.environ.get("GITHUB_OUTPUT", "/dev/null")
SKILL_FOLDER = "spring-boot-best-practices"


def get_script_hash() -> str:
    return hashlib.sha256(SCRIPT_FILE.read_bytes()).hexdigest()[:12]


def _github_headers() -> dict[str, str]:
    headers = {"Accept": "application/vnd.github+json"}
    token = os.environ.get("GITHUB_TOKEN", "")
    if token:
        headers["Authorization"] = f"Bearer {token}"
    return headers


def get_latest_patches() -> dict[str, str]:
    """Return the latest GA patch version for every minor line with releases.

    Returns e.g. {"3.2": "3.2.12", "3.3": "3.3.13", "3.4": "3.4.13", ...}
    """
    resp = httpx.get(
        "https://api.github.com/repos/spring-projects/spring-boot/tags?per_page=100",
        headers=_github_headers(),
        timeout=30,
    )
    resp.raise_for_status()
    tags = [
        t["name"].lstrip("v") for t in resp.json()
        if t["name"].startswith("v") and re.match(r"^v?\d+\.\d+\.\d+$", t["name"])
    ]

    # Group by minor, keep highest patch
    by_minor: dict[str, str] = {}
    for tag in tags:
        parts = tag.split(".")
        minor = f"{parts[0]}.{parts[1]}"
        if minor not in by_minor or list(map(int, tag.split("."))) > list(map(int, by_minor[minor].split("."))):
            by_minor[minor] = tag

    for minor in sorted(by_minor, key=lambda m: list(map(int, m.split("."))), reverse=True):
        print(f"  {minor}.x -> {by_minor[minor]}")

    return by_minor


def set_output(key: str, value: str) -> None:
    with open(GITHUB_OUTPUT, "a") as f:
        f.write(f"{key}={value}\n")


def main() -> None:
    force = "--force" in sys.argv

    # Load current state
    state = json.loads(VERSIONS_FILE.read_text())
    old_hash = state.get("script_hash", "")
    versions: dict[str, dict] = state.get("versions", {})

    # Detect script changes
    new_hash = get_script_hash()
    script_changed = new_hash != old_hash

    # Track which minor versions need regeneration
    to_generate: set[str] = set()

    if script_changed:
        print(f"Script changed: {old_hash} -> {new_hash}")
        for minor in versions:
            to_generate.add(minor)
        state["script_hash"] = new_hash

    # Check for new Spring Boot releases
    print("Checking for new Spring Boot releases...")
    latest_patches = get_latest_patches()

    for minor, meta in versions.items():
        if minor in latest_patches:
            current_patch = meta.get("latest_patch", "")
            if latest_patches[minor] != current_patch:
                print(f"  {minor}.x: patch updated {current_patch} -> {latest_patches[minor]}")
                meta["latest_patch"] = latest_patches[minor]

    # Auto-discover new minor versions (latest minor per major only)
    by_major: dict[int, list[str]] = {}
    for minor in latest_patches:
        major = int(minor.split(".")[0])
        by_major.setdefault(major, []).append(minor)

    for major, minors in by_major.items():
        newest = max(minors, key=lambda m: list(map(int, m.split("."))))
        if newest not in versions:
            print(f"  New minor discovered: {newest}.x (patch {latest_patches[newest]})")
            versions[newest] = {"latest_patch": latest_patches[newest]}
            to_generate.add(newest)

    if force:
        to_generate = set(versions.keys())

    if not to_generate:
        print("No changes detected. Nothing to generate.")
        set_output("releases", "")
        set_output("versions_changed", "false")
        return

    print(f"\nMinor versions to generate: {sorted(to_generate)}")

    # Generate skills and create per-version zips
    OUTPUT_DIR.mkdir(exist_ok=True)
    ZIPS_DIR.mkdir(exist_ok=True)
    releases = []

    for minor in sorted(to_generate):
        meta = versions[minor]
        patch = meta.get("latest_patch", "")
        if not patch:
            print(f"  Skipping {minor}.x — no patch version known")
            continue

        tag = f"v{minor}"
        display = f"{minor}.x"
        print(f"\nGenerating skill for Spring Boot {display} (using {patch} docs)...")

        # Clean output dir so previous version doesn't leak
        skill_dir = OUTPUT_DIR / SKILL_FOLDER
        if skill_dir.exists():
            shutil.rmtree(skill_dir)

        result = subprocess.run(
            [sys.executable, str(SCRIPT_FILE),
             "--version", patch,
             "--display-version", display,
             "--output", str(OUTPUT_DIR),
             "--no-cache"],
            capture_output=True, text=True, timeout=300,
        )
        if result.returncode != 0:
            print(f"  FAILED: {result.stderr[:500]}")
            continue

        print(result.stdout)

        # Create zip immediately while output dir has this version's content
        zip_path = ZIPS_DIR / f"{tag}.zip"
        with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zf:
            for file in sorted(skill_dir.rglob("*")):
                if file.is_file():
                    zf.write(file, f"{SKILL_FOLDER}/{file.relative_to(skill_dir)}")
        print(f"  Zipped: {zip_path}")

        releases.append(f"{minor}:{tag}:{zip_path}")

    # Save updated state
    state["versions"] = versions
    VERSIONS_FILE.write_text(json.dumps(state, indent=2) + "\n")

    # Output for GitHub Actions
    set_output("releases", " ".join(releases))
    set_output("versions_changed", "true" if releases else "false")

    print(f"\nDone. Releases: {releases}")


if __name__ == "__main__":
    main()
