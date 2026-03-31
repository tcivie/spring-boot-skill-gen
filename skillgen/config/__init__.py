"""Configuration: project definitions, compatibility matrix, constants."""

from skillgen.config.projects import ProjectConfig, load_projects
from skillgen.config.constants import (
    CACHE_DIR, MAX_CONCURRENT, SKILL_FOLDER, SKIP_FILES, SKIP_DIRS,
    TEMPLATES_DIR, PROJECTS_FILE, COMPATIBILITY_FILE,
)

__all__ = [
    "ProjectConfig", "load_projects",
    "CACHE_DIR", "MAX_CONCURRENT", "SKILL_FOLDER", "SKIP_FILES", "SKIP_DIRS",
    "TEMPLATES_DIR", "PROJECTS_FILE", "COMPATIBILITY_FILE",
]
