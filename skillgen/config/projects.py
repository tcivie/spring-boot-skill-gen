"""Project configuration: defines how to scrape each Spring project."""

from __future__ import annotations

import json
from dataclasses import dataclass

from skillgen.config.constants import PROJECTS_FILE


@dataclass(frozen=True)
class ProjectConfig:
    """Configuration for a single Spring project."""
    project_id: str
    repo: str           # e.g. "spring-projects/spring-boot"
    tag_prefix: str     # e.g. "v" or ""
    doc_paths: dict[str, str]  # major version -> antora modules path, "*" = wildcard
    modules: list[str]  # e.g. ["reference", "how-to"] or ["ROOT"]

    @property
    def github_api(self) -> str:
        return f"https://api.github.com/repos/{self.repo}"

    @property
    def github_raw(self) -> str:
        return f"https://raw.githubusercontent.com/{self.repo}"

    def tag_for_version(self, version: str) -> str:
        return f"{self.tag_prefix}{version}"

    def doc_path_for_version(self, version: str) -> str:
        major = version.split(".")[0]
        return self.doc_paths.get(major, self.doc_paths.get("*", ""))


def load_projects() -> dict[str, ProjectConfig]:
    """Load all project configs from projects.json."""
    data = json.loads(PROJECTS_FILE.read_text())
    return {
        pid: ProjectConfig(
            project_id=pid,
            repo=p["repo"],
            tag_prefix=p.get("tag_prefix", ""),
            doc_paths=p["doc_paths"],
            modules=p["modules"],
        )
        for pid, p in data.items()
    }
