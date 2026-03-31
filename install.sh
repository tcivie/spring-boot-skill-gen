#!/usr/bin/env bash
# Install a Spring Boot skill for Claude Code
# Usage: curl -fsSL https://raw.githubusercontent.com/Tcivie/spring-boot-skill-gen/main/install.sh | bash -s -- 3.4
set -euo pipefail

VERSION="${1:?Usage: install.sh <major.minor> (e.g. 3.4, 4.0)}"
SKILL_DIR="${HOME}/.claude/skills/spring-boot-best-practices"
REPO="Tcivie/spring-boot-skill-gen"
TAG="v${VERSION}"

# Check the release exists
if ! curl -fsSL --head "https://github.com/${REPO}/releases/tag/${TAG}" >/dev/null 2>&1; then
  echo "No release found for Spring Boot ${VERSION}.x"
  echo "Available versions:"
  curl -fsSL "https://api.github.com/repos/${REPO}/releases" \
    | grep -o '"tag_name":"[^"]*"' \
    | cut -d'"' -f4 \
    | sed 's/^v/  /'
  exit 1
fi

echo "Installing Spring Boot ${VERSION}.x skill (${TAG})..."

# Download and extract
TMPDIR=$(mktemp -d)
curl -fsSL "https://github.com/${REPO}/releases/download/${TAG}/spring-boot-best-practices.zip" -o "${TMPDIR}/skill.zip"

# Remove old version if exists
rm -rf "${SKILL_DIR}"
mkdir -p "${HOME}/.claude/skills"
unzip -q "${TMPDIR}/skill.zip" -d "${HOME}/.claude/skills/"
rm -rf "${TMPDIR}"

echo "Installed to ${SKILL_DIR}"
echo "Restart Claude Code to pick it up."
