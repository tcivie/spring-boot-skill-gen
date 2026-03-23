#!/usr/bin/env python3
"""
CI orchestrator: detect new Spring Boot versions, bump revisions on script changes,
generate skills, and output release info for GitHub Actions.
"""

from __future__ import annotations

import hashlib
import json
import os
import subprocess
import sys
from pathlib import Path

import httpx

VERSIONS_FILE = Path("versions.json")
SCRIPT_FILE = Path("generate_skill.py")
OUTPUT_DIR = Path("output")
GITHUB_OUTPUT = os.environ.get("GITHUB_OUTPUT", "/dev/null")

# Active Spring Boot minor branches to track (latest patch of each)
TRACKED_MINORS = ["3.4", "4.0"]


def get_script_hash() -> str:
    return hashlib.sha256(SCRIPT_FILE.read_bytes()).hexdigest()[:12]


def get_latest_tags() -> dict[str, str]:
    """Fetch the latest patch version for each tracked minor from GitHub."""
    headers = {"Accept": "application/vnd.github+json"}
    token = os.environ.get("GITHUB_TOKEN", "")
    if token:
        headers["Authorization"] = f"Bearer {token}"
    resp = httpx.get(
        "https://api.github.com/repos/spring-projects/spring-boot/tags?per_page=100",
        headers=headers,
        timeout=30,
    )
    resp.raise_for_status()
    import re
    tags = [
        t["name"].lstrip("v") for t in resp.json()
        if t["name"].startswith("v") and re.match(r"^v?\d+\.\d+\.\d+$", t["name"])
    ]

    latest: dict[str, str] = {}
    for minor in TRACKED_MINORS:
        matching = sorted(
            [t for t in tags if t.startswith(f"{minor}.")],
            key=lambda v: list(map(int, v.split("."))),
            reverse=True,
        )
        if matching:
            latest[minor] = matching[0]
    return latest


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

    if script_changed:
        print(f"Script changed: {old_hash} -> {new_hash}")
        # Bump revision for all tracked versions
        for v in versions:
            versions[v]["revision"] = versions[v].get("revision", 0) + 1
        state["script_hash"] = new_hash

    # Check for new Spring Boot releases
    print("Checking for new Spring Boot releases...")
    latest = get_latest_tags()
    versions_changed = script_changed

    for minor, latest_version in latest.items():
        if latest_version not in versions:
            # Find and remove old patch of same minor
            old_patches = [v for v in versions if v.startswith(f"{minor}.")]
            for old in old_patches:
                print(f"  Replacing {old} with {latest_version}")
                del versions[old]
            versions[latest_version] = {"revision": 1}
            versions_changed = True
            print(f"  New version: {latest_version}")

    if not versions_changed and not force:
        print("No changes detected. Nothing to generate.")
        set_output("releases", "")
        set_output("versions_changed", "false")
        return

    # Generate skills
    OUTPUT_DIR.mkdir(exist_ok=True)
    releases = []

    for version, meta in sorted(versions.items()):
        revision = meta.get("revision", 1)
        tag = f"v{version}-r{revision}"
        print(f"\nGenerating skill for Spring Boot {version} (revision {revision})...")

        result = subprocess.run(
            [sys.executable, str(SCRIPT_FILE), "--version", version,
             "--output", str(OUTPUT_DIR), "--no-cache"],
            capture_output=True, text=True, timeout=300,
        )
        if result.returncode != 0:
            print(f"  FAILED: {result.stderr[:500]}")
            continue

        print(result.stdout)

        # Update metadata.version in the generated SKILL.md
        folder = f"spring-boot-{version.replace('.', '-')}"
        skill_md = OUTPUT_DIR / folder / "SKILL.md"
        if skill_md.exists():
            content = skill_md.read_text()
            content = content.replace(
                f'version: "{version}"',
                f'version: "{version}-r{revision}"',
            )
            skill_md.write_text(content)

        releases.append(f"{version}:{tag}")
        meta["revision"] = revision

    # Save updated state
    state["versions"] = versions
    VERSIONS_FILE.write_text(json.dumps(state, indent=2) + "\n")

    # Output for GitHub Actions
    set_output("releases", " ".join(releases))
    set_output("versions_changed", "true" if versions_changed else "false")

    print(f"\nDone. Releases: {releases}")


if __name__ == "__main__":
    main()
