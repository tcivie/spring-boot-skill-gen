"""Display names and formatting for project sections."""

from __future__ import annotations

PROJECT_DISPLAY_NAMES = {
    "boot": "Spring Boot",
    "security": "Spring Security",
    "ai": "Spring AI",
    "modulith": "Spring Modulith",
    "authorization-server": "Spring Authorization Server",
    "cloud-gateway": "Spring Cloud Gateway",
    "cloud-config": "Spring Cloud Config",
    "cloud-netflix": "Spring Cloud Netflix (Eureka)",
    "cloud-openfeign": "Spring Cloud OpenFeign",
    "cloud-circuitbreaker": "Spring Cloud Circuit Breaker",
    "cloud-stream": "Spring Cloud Stream",
    "cloud-function": "Spring Cloud Function",
    "cloud-bus": "Spring Cloud Bus",
    "cloud-consul": "Spring Cloud Consul",
    "cloud-kubernetes": "Spring Cloud Kubernetes",
    "cloud-vault": "Spring Cloud Vault",
    "cloud-commons": "Spring Cloud Commons",
    "cloud-contract": "Spring Cloud Contract",
    "cloud-task": "Spring Cloud Task",
}

SECTION_OVERRIDES = {"io": "IO", "jms": "JMS", "aot": "AOT", "ssl": "SSL"}


def section_title(section: str) -> str:
    """Convert directory name to display title."""
    if section in SECTION_OVERRIDES:
        return SECTION_OVERRIDES[section]
    return section.replace("-", " ").title()
