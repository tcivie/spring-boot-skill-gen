"""Topic discovery via GitHub Trees API."""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

import httpx

from skillgen.config import ProjectConfig, SKIP_FILES, SKIP_DIRS


@dataclass(frozen=True, slots=True)
class DiscoveredTopic:
    """A topic auto-discovered from a Spring project's repo tree."""
    module: str       # "reference", "how-to", or "ROOT"
    section: str      # directory under pages/ e.g. "web", "features", "data"
    adoc_path: str    # relative path from module root e.g. "web/servlet.adoc"
    raw_url: str      # full raw GitHub URL


def _github_headers() -> dict[str, str]:
    headers = {"Accept": "application/vnd.github+json"}
    token = os.environ.get("GITHUB_TOKEN", "")
    if token:
        headers["Authorization"] = f"Bearer {token}"
    return headers


def discover_topics(version: str, config: ProjectConfig) -> list[DiscoveredTopic]:
    """Use GitHub Trees API to find all .adoc topic files for a project."""
    base = config.doc_path_for_version(version)
    tag = config.tag_for_version(version)

    print(f"  Discovering topics from {config.repo}@{tag}...", flush=True)
    resp = httpx.get(
        f"{config.github_api}/git/trees/{tag}?recursive=1",
        headers=_github_headers(),
        timeout=30,
    )
    resp.raise_for_status()
    tree = resp.json()["tree"]

    topics = []
    for entry in tree:
        path = entry["path"]
        for module in config.modules:
            prefix = f"{base}/{module}/pages/"
            if not path.startswith(prefix) or not path.endswith(".adoc"):
                continue

            rel = path[len(prefix):]
            filename = Path(rel).name

            if filename in SKIP_FILES:
                continue
            if any(part in SKIP_DIRS for part in Path(rel).parts):
                continue

            parts = Path(rel).parts
            if len(parts) > 1:
                section = parts[0]
            elif module == "how-to":
                section = "how-to-guides"
            else:
                section = "general"

            topics.append(DiscoveredTopic(
                module=module,
                section=section,
                adoc_path=rel,
                raw_url=f"{config.github_raw}/{tag}/{path}",
            ))

    print(f"  Found {len(topics)} topics across {len(set(t.section for t in topics))} sections")
    return topics
