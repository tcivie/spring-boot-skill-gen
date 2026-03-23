# Contributing

Thanks for your interest in improving the Spring Boot Skill Generator!

## Quick Start

```bash
git clone https://github.com/Tcivie/spring-boot-skill-gen.git
cd spring-boot-skill-gen
pip install httpx
npm install

# Generate a skill locally
python generate_skill.py --version 4.0.4 --output /tmp/test
```

## Project Structure

```
generate_skill.py       # Main generator — discovers, fetches, converts, splits
ci/generate_all.py      # CI orchestrator — version detection, revision tracking
versions.json           # Tracked versions + script hash (auto-updated by CI)
install.sh              # One-liner installer for end users
.github/workflows/      # Daily cron + push triggers
```

## How to Contribute

### Improving the Generator

The most impactful contributions improve output quality:

- **Post-processing cleanup** — leftover AsciiDoc macros or formatting artifacts that slip through `_POST_PATTERNS` in `generate_skill.py`
- **Splitting heuristics** — better logic for when/how to split large files into sub-files
- **SKILL.md template** — improvements to the core principles, anti-pattern table, or "How to Use" section

After making changes, regenerate and compare:

```bash
# Generate before your change
python generate_skill.py --version 4.0.4 --output /tmp/before

# Make your change, then regenerate
python generate_skill.py --version 4.0.4 --output /tmp/after --no-cache

# Compare
diff -r /tmp/before /tmp/after
```

### Adding Tracked Majors

Version discovery is automatic — the CI finds the latest minor per major version. If Spring Boot releases a new major (e.g., 5.x), it will be picked up by the daily cron with no changes needed.

### Reporting Issues

If you spot bad output in a generated skill (garbled text, missing content, leftover macros), please open an issue with:

1. The Spring Boot version
2. The reference file path (e.g., `references/data/nosql/mongodb.md`)
3. What's wrong and what it should look like

## Development Notes

- **Python 3.10+** required (`match` statements, `X | Y` union types)
- **Node.js** required for `downdoc` (AsciiDoc → Markdown conversion)
- **httpx** for async HTTP — don't switch to `urllib` (SSL issues on macOS)
- The generator uses a single Node.js process for batch conversion — don't change this to per-file subprocess calls (30x slower)

## Versioning

Skills are versioned as `<spring-boot-version>-r<revision>`:

- Changing `generate_skill.py` bumps the revision for all tracked versions
- The `script_hash` in `versions.json` detects this automatically
- Don't manually edit revision numbers in `versions.json`

## Code Style

- Keep it simple — this is a ~400 line script, not a framework
- No type: ignore comments — fix the types instead
- Test locally before submitting a PR

## License

By contributing, you agree that your contributions will be licensed under the MIT License.
