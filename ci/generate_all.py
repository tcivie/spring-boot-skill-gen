#!/usr/bin/env python3
"""
CI orchestrator: resolve companion versions for each Boot minor,
generate bundled skills, and output release info for GitHub Actions.
"""

from __future__ import annotations

import hashlib
import json
import os
import re
import subprocess
import sys
import zipfile
from pathlib import Path

import httpx

VERSIONS_FILE = Path("versions.json")
SCRIPT_FILE = Path("generate_skill.py")
PROJECTS_FILE = Path("projects.json")
COMPATIBILITY_FILE = Path("compatibility.json")
OUTPUT_DIR = Path("output")
ZIPS_DIR = Path("zips")
GITHUB_OUTPUT = os.environ.get("GITHUB_OUTPUT", "/dev/null")
SKILL_FOLDER = "spring-best-practices"


def get_script_hash() -> str:
    """Hash the entire skillgen package + entrypoint for change detection."""
    h = hashlib.sha256()
    for f in sorted(Path("skillgen").rglob("*.py")):
        h.update(f.read_bytes())
    h.update(SCRIPT_FILE.read_bytes())
    return h.hexdigest()[:12]


def _github_headers() -> dict[str, str]:
    headers = {"Accept": "application/vnd.github+json"}
    token = os.environ.get("GITHUB_TOKEN", "")
    if token:
        headers["Authorization"] = f"Bearer {token}"
    return headers


def get_latest_patch(repo: str, tag_prefix: str, minor: str) -> str | None:
    """Find the latest GA patch version for a given minor line.

    E.g. minor="6.4" in spring-security → "6.4.13"
    """
    best: str | None = None
    best_tuple: tuple[int, ...] = (0,)
    prefix_re = re.compile(rf"^{re.escape(tag_prefix)}(\d+\.\d+\.\d+)$")

    for page in range(1, 4):
        resp = httpx.get(
            f"https://api.github.com/repos/{repo}/tags?per_page=100&page={page}",
            headers=_github_headers(),
            timeout=30,
        )
        resp.raise_for_status()
        tags = resp.json()
        if not tags:
            break
        for tag in tags:
            m = prefix_re.match(tag["name"])
            if not m:
                continue
            version = m.group(1)
            if not version.startswith(f"{minor}."):
                continue
            v_tuple = tuple(map(int, version.split(".")))
            if v_tuple > best_tuple:
                best = version
                best_tuple = v_tuple
        if best:
            break  # Found at least one match, no need to paginate

    return best


def resolve_cloud_versions(train_minor: str) -> dict[str, str]:
    """Fetch the Cloud BOM for a train and return subproject version map.

    E.g. train_minor="2024.0" → {"cloud-gateway": "4.2.7", "cloud-config": "4.2.4", ...}
    """
    # Find latest patch of the train (paginate — older trains are on page 2+)
    train_re = re.compile(rf"^v{re.escape(train_minor)}\.(\d+)$")
    best_patch = -1
    best_tag = ""

    for page in range(1, 4):
        resp = httpx.get(
            f"https://api.github.com/repos/spring-cloud/spring-cloud-release/tags?per_page=100&page={page}",
            headers=_github_headers(),
            timeout=30,
        )
        resp.raise_for_status()
        tags = resp.json()
        if not tags:
            break
        for tag in tags:
            m = train_re.match(tag["name"])
            if m:
                patch = int(m.group(1))
                if patch > best_patch:
                    best_patch = patch
                    best_tag = tag["name"]
        if best_tag:
            break  # Found it, no need to paginate further

    if not best_tag:
        print(f"  Warning: no Cloud train tag found for {train_minor}")
        return {}

    print(f"  Cloud train: {best_tag}")

    # Fetch the BOM POM
    resp = httpx.get(
        f"https://api.github.com/repos/spring-cloud/spring-cloud-release/contents/spring-cloud-dependencies/pom.xml?ref={best_tag}",
        headers=_github_headers(),
        timeout=30,
    )
    resp.raise_for_status()

    import base64
    pom_xml = base64.b64decode(resp.json()["content"]).decode()

    # Parse version properties from POM
    versions: dict[str, str] = {}
    cloud_projects = [
        "gateway", "config", "netflix", "openfeign", "circuitbreaker",
        "stream", "function", "bus", "consul", "kubernetes",
        "vault", "commons", "contract", "task",
    ]

    for project in cloud_projects:
        pattern = rf"<spring-cloud-{project}\.version>([\d.]+)</spring-cloud-{project}\.version>"
        m = re.search(pattern, pom_xml)
        if m:
            versions[f"cloud-{project}"] = m.group(1)

    return versions


def set_output(key: str, value: str) -> None:
    with open(GITHUB_OUTPUT, "a") as f:
        f.write(f"{key}={value}\n")


def main() -> None:
    force = "--force" in sys.argv

    # Load configuration
    projects_config = json.loads(PROJECTS_FILE.read_text())
    compatibility = json.loads(COMPATIBILITY_FILE.read_text())

    # Load current state
    state = json.loads(VERSIONS_FILE.read_text())
    old_hash = state.get("script_hash", "")
    versions: dict[str, dict] = state.get("versions", {})

    # Detect script/package changes
    new_hash = get_script_hash()
    script_changed = new_hash != old_hash

    to_generate: set[str] = set()

    if script_changed:
        print(f"Script changed: {old_hash} -> {new_hash}")
        to_generate = set(versions.keys())
        state["script_hash"] = new_hash

    # Check for new Boot releases (latest patch per tracked minor)
    print("Checking for new Spring Boot releases...")
    boot_config = projects_config["boot"]
    resp = httpx.get(
        f"https://api.github.com/repos/{boot_config['repo']}/tags?per_page=100",
        headers=_github_headers(),
        timeout=30,
    )
    resp.raise_for_status()
    boot_tags = [
        t["name"].lstrip("v") for t in resp.json()
        if re.match(r"^v\d+\.\d+\.\d+$", t["name"])
    ]

    # Group by minor
    boot_by_minor: dict[str, str] = {}
    for tag in boot_tags:
        parts = tag.split(".")
        minor = f"{parts[0]}.{parts[1]}"
        v_tuple = tuple(map(int, tag.split(".")))
        if minor not in boot_by_minor or v_tuple > tuple(map(int, boot_by_minor[minor].split("."))):
            boot_by_minor[minor] = tag

    # Update tracked versions with new Boot patches
    for boot_minor, meta in versions.items():
        if boot_minor in boot_by_minor:
            current_boot = meta.get("boot", "")
            latest_boot = boot_by_minor[boot_minor]
            if latest_boot != current_boot:
                print(f"  Boot {boot_minor}.x: {current_boot} -> {latest_boot}")
                meta["boot"] = latest_boot

    if force:
        to_generate = set(versions.keys())

    if not to_generate:
        print("No changes detected. Nothing to generate.")
        set_output("releases", "")
        set_output("versions_changed", "false")
        return

    print(f"\nBoot minors to generate: {sorted(to_generate)}")

    # Resolve companion versions and generate
    OUTPUT_DIR.mkdir(exist_ok=True)
    ZIPS_DIR.mkdir(exist_ok=True)
    releases = []

    for boot_minor in sorted(to_generate):
        meta = versions.get(boot_minor, {})
        compat = compatibility.get(boot_minor, {})
        if not compat:
            print(f"\n  Skipping {boot_minor}.x — no compatibility entry")
            continue

        boot_patch = meta.get("boot", "")
        if not boot_patch:
            # Try to resolve it
            boot_patch = boot_by_minor.get(boot_minor, "")
            if boot_patch:
                meta["boot"] = boot_patch

        if not boot_patch:
            print(f"\n  Skipping {boot_minor}.x — no Boot patch version")
            continue

        display = f"{boot_minor}.x"
        tag = f"v{boot_minor}"
        print(f"\n{'='*60}")
        print(f"Generating bundled skill for Spring {display}")
        print(f"{'='*60}")

        # Build companions dict: project_id -> exact patch version
        companions: dict[str, str] = {"boot": boot_patch}

        # Resolve non-Cloud companions
        for project_id, minor in compat.items():
            if project_id in ("boot", "cloud_train"):
                continue
            pconf = projects_config.get(project_id, {})
            repo = pconf.get("repo", "")
            tag_prefix = pconf.get("tag_prefix", "")
            if not repo:
                continue

            patch = get_latest_patch(repo, tag_prefix, minor)
            if patch:
                companions[project_id] = patch
                meta[project_id] = patch
                print(f"  {project_id}: {minor}.x -> {patch}")
            else:
                print(f"  {project_id}: {minor}.x -> NOT FOUND (skipping)")

        # Resolve Cloud subproject versions from BOM
        cloud_train = compat.get("cloud_train", "")
        if cloud_train:
            cloud_versions = resolve_cloud_versions(cloud_train)
            meta["cloud_train"] = cloud_train
            for cloud_id, cloud_version in cloud_versions.items():
                if cloud_id in projects_config:
                    companions[cloud_id] = cloud_version
                    meta[cloud_id] = cloud_version
                    print(f"  {cloud_id}: {cloud_version}")

        # Generate the bundled skill
        companions_json = json.dumps(companions)
        result = subprocess.run(
            [sys.executable, str(SCRIPT_FILE),
             "--bundled",
             "--companions", companions_json,
             "--display-version", display,
             "--output", str(OUTPUT_DIR),
             "--no-cache"],
            capture_output=True, text=True, timeout=600,
        )
        if result.returncode != 0:
            print(f"  FAILED: {result.stderr[:500]}")
            continue

        print(result.stdout)

        # Zip the output
        skill_dir = OUTPUT_DIR / SKILL_FOLDER
        zip_path = ZIPS_DIR / f"{SKILL_FOLDER}-{boot_minor}.zip"
        with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zf:
            for file in sorted(skill_dir.rglob("*")):
                if file.is_file():
                    zf.write(file, f"{SKILL_FOLDER}/{file.relative_to(skill_dir)}")
        print(f"  Zipped: {zip_path}")

        versions[boot_minor] = meta
        releases.append(f"{boot_minor}:{tag}:{zip_path}")

    # Save updated state
    state["versions"] = versions
    VERSIONS_FILE.write_text(json.dumps(state, indent=2) + "\n")

    # Output for GitHub Actions
    set_output("releases", " ".join(releases))
    set_output("versions_changed", "true" if releases else "false")

    print(f"\nDone. Releases: {releases}")


if __name__ == "__main__":
    main()
