"""Shared constants and paths."""

from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
PROJECTS_FILE = REPO_ROOT / "projects.json"
COMPATIBILITY_FILE = REPO_ROOT / "compatibility.json"
TEMPLATES_DIR = REPO_ROOT / "templates"
CACHE_DIR = Path(".skill_cache")
SKILL_FOLDER = "spring-best-practices"
MAX_CONCURRENT = 10

SKIP_FILES = {"index.adoc", "nav.adoc", "_attributes.adoc"}
SKIP_DIRS = {"partials"}
