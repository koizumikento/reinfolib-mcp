import assert from "node:assert/strict";
import { readFile } from "node:fs/promises";
import { test, afterEach } from "node:test";

const source = await readFile(new URL("../worker/index.js", import.meta.url), "utf8");
const { default: worker } = await import(`data:text/javascript;base64,${Buffer.from(source).toString("base64")}`);
const env = { REINFOLIB_BACKEND_URL: "https://backend.invalid/mcp",
  REINFOLIB_BACKEND_TOKEN: "synthetic-service-token-for-tests-only" };
const originalFetch = globalThis.fetch;
afterEach(() => { globalThis.fetch = originalFetch; });
const request = (message, headers = {}, method = "POST") => new Request("https://site.invalid/mcp", {
  method, headers: { "oai-authenticated-user-id": "fixture-user",
    "Content-Type": "application/json", Accept: "application/json, text/event-stream", ...headers },
  ...(method === "POST" ? { body: typeof message === "string" ? message : JSON.stringify(message) } : {}),
});
const call = { jsonrpc: "2.0", id: 1, method: "tools/call",
  params: { name: "reinfolib_get_api_data", arguments: { api_id: "XIT002", parameters: { area: "13" } } } };

test("authorization, origin and protocol rejections never reach backend", async () => {
  globalThis.fetch = () => { throw new Error("Unexpected forwarding"); };
  const cases = [
    [request(call, { "oai-authenticated-user-id": "" }), 401],
    [request(call, { "oai-authenticated-user-id": "", "OAI-Sites-Authorization": "Bearer bypass" }), 401],
    [request(call, { Origin: "https://attacker.invalid" }), 403],
    [request(null, {}, "GET"), 405],
    [request(call, { "Content-Type": "text/plain" }), 415],
    [request(call, { Accept: "application/json" }), 406],
    [request("invalid"), 400],
    [request([call]), 400],
    [request({ ...call, id: null }), 400],
    [request({ ...call, method: "unknown" }), 400],
    [request({ ...call, method: "notifications/initialized" }), 400],
    [request({ jsonrpc: "2.0", method: "tools/list" }), 400],
    [request(" ".repeat(65537)), 413],
  ];
  for (const [req, status] of cases) assert.equal((await worker.fetch(req, env)).status, status);
});

test("fixed backend, clean service headers, protocol version and exact result bytes", async () => {
  const body = JSON.stringify({ jsonrpc: "2.0", id: 1, result: {
    content: [{ type: "text", text: "fixture provenance / JSON / GeoJSON / PBF" }],
  } });
  globalThis.fetch = async (url, options) => {
    assert.equal(url.href, env.REINFOLIB_BACKEND_URL);
    assert.equal(options.redirect, "manual");
    assert.equal(options.headers.get("Authorization"), `Bearer ${env.REINFOLIB_BACKEND_TOKEN}`);
    assert.equal(options.headers.get("MCP-Protocol-Version"), "2025-03-26");
    assert.equal(options.headers.get("Mcp-Method"), "tools/call");
    assert.equal(options.headers.get("Mcp-Name"), call.params.name);
    assert.equal(options.headers.get("Cookie"), null);
    assert.equal(options.headers.get("Origin"), null);
    assert.equal(options.headers.get("oai-authenticated-user-id"), null);
    assert.deepEqual(JSON.parse(options.body), call);
    return new Response(body, { headers: { "Content-Type": "application/json", "Set-Cookie": "private" } });
  };
  const result = await worker.fetch(request(call, {
    Authorization: "Bearer visitor", Cookie: "private", "MCP-Protocol-Version": "2025-03-26",
    "Mcp-Method": "forged", "Mcp-Name": "forged",
  }), env);
  assert.equal(await result.text(), body);
  assert.equal(result.headers.get("Set-Cookie"), null);
  assert.equal(result.headers.get("Cache-Control"), "no-store");
});

test("notification and streamed SSE are passed through", async () => {
  globalThis.fetch = async () => new Response(null, { status: 202 });
  assert.equal((await worker.fetch(request({ jsonrpc: "2.0", method: "notifications/initialized" }), env)).status, 202);
  globalThis.fetch = async () => new Response("data: fixture\n\n", { headers: { "Content-Type": "text/event-stream" } });
  assert.equal(await (await worker.fetch(request(call), env)).text(), "data: fixture\n\n");
});

test("missing config, redirects and errors do not leak backend secrets", async () => {
  for (const change of [{ REINFOLIB_BACKEND_URL: "http://backend.invalid/mcp" },
    { REINFOLIB_BACKEND_URL: "https://backend.invalid/other" },
    { REINFOLIB_BACKEND_TOKEN: "" }]) {
    assert.equal((await worker.fetch(request(call), { ...env, ...change })).status, 503);
  }
  for (const status of [302, 401, 403, 429, 500]) {
    globalThis.fetch = async () => new Response(env.REINFOLIB_BACKEND_TOKEN, { status });
    const response = await worker.fetch(request(call), env);
    assert.equal(response.status, 502);
    assert.ok(!(await response.text()).includes(env.REINFOLIB_BACKEND_TOKEN));
  }
  globalThis.fetch = async () => { throw new Error(env.REINFOLIB_BACKEND_TOKEN); };
  assert.equal((await worker.fetch(request(call), env)).status, 502);
});
