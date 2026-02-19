# annotator

AI-powered code documentation agent. Analyzes Python and TypeScript/JavaScript source
files and generates missing docstrings, JSDoc comments, and OpenAPI/Postman spec updates
using Claude AI.

## Features

- Detects functions and API endpoints missing documentation
- Generates PEP-257 compliant Python docstrings
- Generates JSDoc comments for TypeScript/JavaScript
- Detects FastAPI, Flask, Express, and NestJS endpoints
- Updates OpenAPI/Swagger YAML/JSON specs (comment-preserving)
- Updates Postman Collection files
- Interactive diff viewer with per-symbol confirmation
- Optional git pre-commit integration

## Installation

```bash
pip install ai-annotator
```

## Requirements

- Python 3.10+
- An Anthropic API key

```bash
export ANTHROPIC_API_KEY=your_key_here
```

## Usage

```bash
# Analyze all supported files in the current directory
annotator run .

# Analyze a specific directory
annotator run src/

# Analyze a single file
annotator run src/api/users.py

# Only analyze git-staged files
annotator run --staged

# Accept all proposals without prompting
annotator run . --all

# Dry-run: show what would change, no modifications
annotator check .

# Dry-run on staged files
annotator check --staged
```

## Interactive Prompt

For each symbol with a missing docstring, annotator shows the proposed documentation
and asks:

```
Apply? [y]es / [n]o / [s]how diff / [a]ll (accept all remaining)
```

## Supported Languages

| Language | Framework Detection | Doc Format |
|----------|--------------------|----|
| Python | FastAPI, Flask | PEP-257 docstrings |
| TypeScript | Express, NestJS | JSDoc |
| JavaScript | Express | JSDoc |

## OpenAPI/Swagger Integration

If an OpenAPI spec is found (`openapi.yaml`, `swagger.json`, etc.), annotator will
offer to update the relevant path/operation when an API endpoint is documented.

Spec files are searched in: `.`, `docs/`, `api/`, `spec/`

## Postman Integration

If a `*.postman_collection.json` file is found, annotator will offer to add or update
the corresponding request.

## Optional Pre-commit Integration

Add to your `.pre-commit-config.yaml`:

```yaml
repos:
  - repo: https://github.com/annotator-dev/annotator
    rev: v0.1.0
    hooks:
      - id: annotator
```

This runs `annotator run --staged` on staged Python/TypeScript files before each commit.

## Claude Code Skill

Install as a Claude Code skill by adding `SKILL.md` to your skills directory.
Then use `/annotator [path]` directly in Claude Code.

## Development

```bash
git clone https://github.com/annotator-dev/annotator
cd annotator
pip install -e ".[dev]"
pytest
```

## License

MIT
