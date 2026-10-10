# Sites MCP adapter

Sites Worker ESM → authenticated HTTPS Python backend → MLIT API.
This is a local implementation and review artifact; no Site, plugin, backend,
tunnel or account has been provisioned by this change.

The Worker exposes stateless `POST /mcp`. The backend reuses all 13 existing
MCP tools and all 35 API contracts. Python library/CLI/stdio/http/sse remain
available. No Python package executes inside the Sites Worker: a separately
operated Python backend is required. This avoids a second implementation of
API validation, retries, rate limits, geospatial assembly and tool schemas.

## Build and verify

From the repository root (Node.js 22+ and current uv):

```sh
uv sync --frozen --extra dev
uv run pytest -q
uv run --extra dev mypy src/reinfolib_mcp
node --test sites/tests/worker.test.mjs
node sites/scripts/build.mjs
uv build
```

`sites/dist/server/index.js` is a dependency-free ESM module exporting
`default.fetch(request, env, ctx)`; `sites/dist/.openai/hosting.json` declares
`capabilities: ["mcp"]`. The layout and build follow the official Worker ESM
starter. The Node build also validates the export and manifest. No storage,
browser application, OAuth implementation or arbitrary forwarding tool is added.

## Backend operation

Provide these names through the backend host's runtime secret/environment
facility (never command-line values or tracked files):

| Name | Purpose |
| --- | --- |
| `REINFOLIB_API_KEY` | MLIT subscription key, backend only |
| `REINFOLIB_BACKEND_TOKEN` | Dedicated random service credential, at least 32 characters; use 32 random bytes or more |
| `REINFOLIB_BACKEND_HOST` | Exact backend HTTP Host, including port when used (e.g. `backend.example.com`) |

Start one process on loopback:

```sh
uv run uvicorn reinfolib_mcp.sites_backend:create_app --factory --host 127.0.0.1 --port 8000 --no-access-log
```

Keep it supervised by the existing hosting system; use one process per API key
because the existing 60 requests/minute throttle is in-process and shared by
the tools. Multiple processes/replicas require a coordinated rate limiter first.
Upstream 429 remains `RateLimitError`; it is not silently retried or changed to
an empty success. Existing timeout/retry behavior remains in the Python client.

Expose **only `/mcp`** over HTTPS through an existing TLS reverse proxy, or a
named Cloudflare Tunnel with an HTTP origin service at `http://127.0.0.1:8000`.
Set its public hostname to match `REINFOLIB_BACKEND_HOST` and preserve that Host
at the origin. Set a 64 KiB request-body limit at an HTTP reverse proxy if used.
The dedicated token is verified at the Python endpoint even when a tunnel is
used. No inbound Python port or unauthenticated backend is required. The Worker
does not accept redirects or URLs supplied in tool arguments.

A tunnel is an optional way to expose the backend's loopback HTTP listener;
it does not give Sites access to private IPs, raw TCP or local stdio. A stable
hostname, running backend, trusted TLS and secret provisioning are operational
prerequisites, not demonstrated by the build. Do not use a temporary public
quick tunnel as the production backend. No additional Cloudflare Access policy
is assumed: adding one requires a separately configured service credential.

## Sites deployment handoff

Use `sites/` as the source root in the official Sites local workflow. In a
deployment checkout, preserve any existing Site `project_id` and audience;
for a new private Site persist the real returned ID into `.openai/hosting.json`
using the Sites `set-project-id.mjs` helper. The repository template intentionally
has no invented Site ID. Do not copy identity or runtime secrets between Sites.

Configure only these server-side runtime names through native Sites tools:

| Name | Purpose |
| --- | --- |
| `REINFOLIB_BACKEND_URL` | Exact `https://<backend-host>/mcp`, with no credentials/query/fragment |
| `REINFOLIB_BACKEND_TOKEN` | Same dedicated backend service credential |

`.env.example` contains names only and is not consumed by the Worker build.
Keep real local env files untracked. The MLIT key stays on the backend and is
never sent to Sites, the browser, the manifest or a model prompt.

Run `node scripts/build.mjs` from the Sites source root, then use the official
Sites source synchronization/package/save/private-deployment helpers on that
source revision and its `dist/` artifact. No `static` binding is needed. Do not
change existing plugin registrations as part of this PR. After an authorized
deployment, separately verify `get_site(include_mcp_connection: true)`, authenticated
initialization, discovery of the 13 tools and an allowed read-only call from the
installed client. A build or HTTP 200 alone does not establish those facts.

## Authorization and result contract

Sites owns OAuth. The Worker trusts `oai-authenticated-user-id` **only behind
Sites Dispatch**, and requires a nonblank identity even for discovery. The
Site's audience controls who can enter; every admitted signed-in user may use
this shared public MLIT data/key quota. Keep an owner-private audience unless
sharing that quota has been authorized. A service bypass bearer does not supply
a user identity and is rejected. Never expose this Worker outside Dispatch
where callers could forge the identity header.

The Worker discards visitor tokens, cookies, identity and routing headers; only
its own backend credential, content negotiation and MCP protocol-version header
reach the fixed backend. Required modern `Mcp-Method` / `Mcp-Name` headers are
regenerated from the body, rather than trusting caller routing headers.
That credential authorizes public-data service calls,
not user records or connected-app consent. The backend verifies a SHA-256 token
digest with constant-time comparison, rejects foreign Host/Origin and uses
stateless JSON HTTP responses. FastMCP performs negotiation/schema validation,
discovery pagination and calls for supported modern/legacy protocol revisions;
the Worker preserves responses without truncation or reserialization.

JSON/GeoJSON results, counts, source fields, paging, empty results and application
`error`/`error_type` fields are preserved. PBF bytes cannot be JSON: MCP now
returns `{"data": "<base64>", "format": "pbf", "encoding": "base64"}` including
nested geospatial results. Decode `data` as standard base64; the Python library
continues returning raw bytes. Unexpected execution errors are masked; existing
actionable API errors are retained. Protocol failures remain JSON-RPC errors;
adapter/backend-connectivity failures return HTTP 4xx/5xx and never expose raw
backend errors or credentials. Requests are capped at 64 KiB. Large response
bodies stream through the Worker; backend memory and downstream client limits
still apply. GET/DELETE return 405; no sessions, background tasks or resumable
SSE stream are advertised.

Protocol/runtime references checked 2026-10-10:

- [MCP Streamable HTTP](https://modelcontextprotocol.io/specification/2025-11-25/basic/transports)
- [Official MCP Python SDK](https://github.com/modelcontextprotocol/python-sdk)
- [FastMCP HTTP and stateless deployment](https://gofastmcp.com/deployment/http)
- [FastMCP token verification](https://gofastmcp.com/servers/auth/token-verification)
- [Cloudflare Tunnel HTTP origin](https://developers.cloudflare.com/cloudflare-one/networks/connectors/cloudflare-tunnel/)

The checked lock contains FastMCP 4.0.10 / MCP SDK 2.2.0; no dependency update
is needed. Local tests use synthetic fixtures, including all 35 API IDs, schema
parity, errors and non-UTF-8 PBF. Loopback SDK calls assert negotiated modern
`2026-07-28` and legacy `2025-11-25` rather than treating fallback as modern success.
They do not prove actual Sites Dispatch identity,
live MLIT responses, tunnel operation, authenticated deployment discovery or
client acceptance. Those are separate deployment checks.
