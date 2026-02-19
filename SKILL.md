# annotator

Analyze source code files and generate missing documentation using Claude AI.
Supports Python (FastAPI/Flask) and TypeScript/JS (Express/NestJS).
Updates OpenAPI/Swagger and Postman Collections when API endpoints change.

## Usage

```
/annotator [path]       Annotate files at path (defaults to current directory)
/annotator check        Dry-run: show what would change without modifying files
```

## Instructions

When the user invokes `/annotator`, do the following:

1. Determine the target path from the argument (default: `.`)
2. Run `annotator run <path>` using the Bash tool
3. If the user says "check" or "dry-run", run `annotator check <path>` instead
4. Report the summary back to the user

## Tools allowed

- Bash (annotator run, annotator check, git diff, git add)
- Read, Edit, Glob, Grep

## Requirements

- ANTHROPIC_API_KEY must be set in the environment
- Install with: `pip install ai-annotator`
