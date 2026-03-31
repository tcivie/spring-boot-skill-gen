"""Discovery: finding .adoc topics in GitHub repos and fetching their content."""

from skillgen.discovery.topics import DiscoveredTopic, discover_topics
from skillgen.discovery.fetch import fetch_all
from skillgen.discovery.metadata import extract_title, extract_keywords

__all__ = [
    "DiscoveredTopic", "discover_topics",
    "fetch_all",
    "extract_title", "extract_keywords",
]
