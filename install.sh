#!/usr/bin/env bash
# Install a Spring Boot skill for Claude Code
# Usage: curl -fsSL https://raw.githubusercontent.com/Tcivie/spring-boot-skill-gen/main/install.sh | bash -s -- 4.0.4
set -euo pipefail

VERSION="${1:?Usage: install.sh <spring-boot-version> (e.g. 4.0.4)}"
SKILL_DIR="${HOME}/.claude/skills/spring-boot-best-practices"
REPO="Tcivie/spring-boot-skill-gen"

# Find the latest release tag for this version
TAG=$(curl -fsSL "https://api.github.com/repos/${REPO}/releases" \
  | grep -o "\"tag_name\":\"v${VERSION}-r[0-9]*\"" \
  | head -1 \
  | cut -d'"' -f4)

if [ -z "$TAG" ]; then
  echo "No release found for Spring Boot ${VERSION}"
  echo "Available versions:"
  curl -fsSL "https://api.github.com/repos/${REPO}/releases" \
    | grep -o '"tag_name":"[^"]*"' \
    | cut -d'"' -f4
  exit 1
fi

echo "Installing Spring Boot ${VERSION} skill (${TAG})..."

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
