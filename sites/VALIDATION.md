# Local validation record (2026-10-10)

Base: fetched `origin/main` at `07778b8`. Synthetic fixture revision: 2026-10-10.
No live MLIT key, customer data, Site, plugin, backend or tunnel was used.

- Python 3.12.13 / FastMCP 4.0.10 / MCP SDK 2.2.0; frozen lock unchanged.
- 123 pytest tests passed, including all 35 API IDs over authenticated HTTP,
  exact 13-tool discovery parity, Host/Origin/token denial, missing/invalid
  inputs, upstream 401/429/500, non-UTF-8 PBF and Python-library bytes retention.
- Real loopback SDK → Node Worker gateway → Uvicorn backend calls passed.
  The gateway simulates Sites Dispatch identity and redirects the fixed HTTPS
  URL to loopback; neither real Dispatch nor TLS/tunnel behavior is claimed.
  Negotiated protocols are asserted as modern 2026-07-28 and legacy 2025-11-25.
  Both child processes are terminated/waited in `finally` on success or failure.
- 4 Node Worker checks passed: request/auth bounds, fixed forwarding/headers,
  notification/SSE passthrough, config/redirect/upstream error secrecy.
- Lock check, mypy, Ruff, isort, Black on src/tests, Sites ESM build,
  Python sdist/wheel build and clean isolated wheel import/tool/PBF checks passed.
  Existing examples passed Ruff/isort; their pre-existing Black formatting
  differences were left unchanged.
- Self-review found and corrected binary PBF JSON serialization and modern
  `server/discover` / required routing-header handling. Modern tests now assert
  the negotiated version so legacy fallback cannot produce a false pass.

Artifact SHA-256 before removal:

- Worker: `db05b5dfcf317bbb7e2629a0b4d508b328d63a08b31b0e80202cfb0ba97bb200`
- Wheel: `2c079db2789ae0960b34a69fdd892174b69b2cc3ff0bf9569b128e78f6625e65`

Cleanup: no test child process remains. Dedicated uv caches at
`<worktree>/.validation-cache` and
`C:/Users/horad/Documents/Codex/2026-10-10/reinfolib-mcp-sites-mcp-pr/work/isolated-wheel-cache`
were removed with scoped `uv cache clean`; `.ruff_cache` was removed using
`ruff clean`. Shared caches and the original checkout were preserved.

PowerShell recursive deletion of owned verification directories was rejected
by automatic approval review (`blocked by policy`). Remaining ignored resources
under `C:/workspace/worktrees/reinfolib-mcp-sites-mcp-support` require cleanup:
`.venv`, `.pytest_cache`, `.mypy_cache`, `src/reinfolib_mcp/__pycache__`,
`tests/__pycache__`, `dist`, and `sites/dist`. They contain local dependencies,
cache or reproducible build output; they are not required source deliverables.
The branch/worktree, tests and this evidence record are intentionally retained
for review. Cleanup is therefore partial, not complete.

GitHub CI/review/mergeability are reported separately in the PR handoff.
Actual Sites deployment, authenticated Dispatch discovery, live MLIT calls,
TLS/tunnel operation and an installed Sites client's call remain untested.
