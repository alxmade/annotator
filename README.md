# annotator

Claude Code plugin that analyzes Python and TypeScript/JS source code and automatically generates missing documentation.

No API keys. No pip install. No CLI. Just Claude Code.

## What it does

- Detects functions and methods without docstrings or JSDoc
- Detects API endpoints (FastAPI, Flask, Express, NestJS)
- Generates PEP-257 docstrings and JSDoc comments
- Updates OpenAPI/Swagger specs when endpoints are documented
- Updates Postman collections when endpoints are documented
- Auto-detects git repos and analyzes only changed files
- Falls back to full directory scan when no git changes are found

## Installation

Inside Claude Code, run these two commands:

```
/plugin marketplace add alxmade/annotator
/plugin install annotator@alxmade
```

The first command registers the marketplace (only needed once).
The second installs the plugin.

## Usage

```
/annotator              Analyze current directory (or git diff if in a repo)
/annotator src/         Analyze a specific directory
/annotator src/api.py   Analyze a single file
/annotator --dry        Show what would change without modifying files
/annotator --diff       Force git-diff mode
```

## How it works

1. Checks if you are in a git repository
2. If yes: analyzes files changed since last commit (git diff HEAD)
3. If no: scans the target directory for .py, .ts, .js files
4. Reads each file and identifies undocumented symbols
5. Generates appropriate documentation (docstrings / JSDoc)
6. Applies all changes at once, no per-symbol confirmation
7. Searches for openapi.yaml or .postman_collection.json and updates them
8. Prints a summary of everything that changed

## Supported languages and frameworks

| Language | Frameworks detected |
|----------|-------------------|
| Python | FastAPI, Flask |
| TypeScript | Express, NestJS |
| JavaScript | Express |

## Requirements

- Claude Code
- That's it

## License

MIT
