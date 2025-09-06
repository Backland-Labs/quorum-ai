Refer to AGENTS.md for more details.

You run in an environment where `ast-grep` is available. Whenever a search requires syntax‑aware or structural matching, default to `ast-grep run --lang <language> -p '<pattern>'` or set `--lang` appropriately, and avoid falling back to text‑only tools like `rg` or `grep` unless I explicitly request a plain‑text search. You can run `ast-grep --help` for more info.

## Development Server

To run the backend development server:

```bash
export $(cat .env | xargs) && export SAFE_CONTRACT_ADDRESSES='{"base":                                            │
│   "0x07edA994E013AbC8619A5038455db3A6FBdd2Bca"}' && cd backend && uv run uvicorn main:app --host 0.0.0.0 --port     │
│   8000
```

**Important**: The `--reload` flag in uvicorn may not work reliably for detecting file changes. If you make code changes and they don't take effect, manually restart the server by killing the process and running the command again.
