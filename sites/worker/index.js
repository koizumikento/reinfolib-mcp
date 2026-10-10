// Sites Dispatch owns authentication and supplies the trusted visitor identity.
const methods = new Set(["initialize", "server/discover", "ping", "tools/list", "tools/call",
  "notifications/initialized", "notifications/cancelled"]);
const maxBody = 64 * 1024;
const json = (body, status = 200) => Response.json(body, {
  status, headers: { "Cache-Control": "no-store" },
});
const error = (id, code, message, status = 400) =>
  json({ jsonrpc: "2.0", id, error: { code, message } }, status);

export default {
  async fetch(request, env) {
    const url = new URL(request.url);
    if (url.pathname !== "/mcp") return new Response("Not found", { status: 404 });
    const origin = request.headers.get("Origin");
    if (origin && origin !== url.origin) return new Response("Forbidden origin", { status: 403 });
    if (request.method !== "POST") return new Response(null, {
      status: 405, headers: { Allow: "POST" },
    });
    // Service bypass is not a signed-in user and cannot spend the upstream API quota.
    if (!request.headers.get("oai-authenticated-user-id")?.trim()) {
      return new Response("Sign in to this Site", { status: 401 });
    }
    if (request.headers.get("Content-Type")?.split(";")[0].trim() !== "application/json") {
      return error(null, -32600, "Use application/json", 415);
    }
    const accept = request.headers.get("Accept") ?? "";
    if (!accept.includes("application/json") || !accept.includes("text/event-stream")) {
      return error(null, -32600, "Accept application/json and text/event-stream", 406);
    }
    let message;
    try {
      const reader = request.body?.getReader();
      const chunks = [];
      let size = 0;
      if (reader) {
        while (true) {
          const { done, value } = await reader.read();
          if (done) break;
          size += value.byteLength;
          if (size > maxBody) {
            await reader.cancel();
            return error(null, -32600, "Request exceeds 64 KiB", 413);
          }
          chunks.push(value);
        }
      }
      const bytes = new Uint8Array(size);
      let offset = 0;
      for (const chunk of chunks) { bytes.set(chunk, offset); offset += chunk.length; }
      message = JSON.parse(new TextDecoder("utf-8", { fatal: true }).decode(bytes));
    } catch {
      return error(null, -32700, "Invalid JSON");
    }
    if (!message || Array.isArray(message) || message.jsonrpc !== "2.0" ||
        typeof message.method !== "string" ||
        ("id" in message && typeof message.id !== "string" &&
          !(typeof message.id === "number" && Number.isSafeInteger(message.id)))) {
      return error(null, -32600, "Invalid JSON-RPC request");
    }
    const id = message.id ?? null;
    if (!methods.has(message.method)) return error(id, -32601, "Method not found");
    if ((message.method.startsWith("notifications/")) !== !("id" in message)) {
      return error(id, -32600, "Requests require an id; notifications must omit it");
    }
    let backend;
    try {
      backend = new URL(env.REINFOLIB_BACKEND_URL);
      if (backend.protocol !== "https:" || backend.username || backend.password ||
          backend.pathname !== "/mcp" || backend.search || backend.hash ||
          typeof env.REINFOLIB_BACKEND_TOKEN !== "string" ||
          env.REINFOLIB_BACKEND_TOKEN.length < 32) throw new Error();
    } catch {
      return error(id, -32603, "Backend runtime configuration is missing or invalid", 503);
    }
    const headers = new Headers({
      "Content-Type": "application/json",
      Accept: "application/json, text/event-stream",
      Authorization: `Bearer ${env.REINFOLIB_BACKEND_TOKEN}`,
      "Mcp-Method": message.method,
    });
    if (message.method === "tools/call" && typeof message.params?.name === "string") {
      headers.set("Mcp-Name", message.params.name);
    }
    const version = request.headers.get("MCP-Protocol-Version");
    if (version) headers.set("MCP-Protocol-Version", version);
    try {
      const response = await fetch(backend, {
        method: "POST", headers, body: JSON.stringify(message), redirect: "manual",
      });
      if (response.status >= 300 && response.status !== 400 && response.status !== 406) {
        await response.body?.cancel();
        return error(id, -32603, "Backend unavailable; check backend access and health", 502);
      }
      const contentType = response.headers.get("Content-Type") ?? "";
      if (response.status !== 202 && !contentType.startsWith("application/json") &&
          !contentType.startsWith("text/event-stream")) {
        await response.body?.cancel();
        return error(id, -32603, "Unexpected backend response", 502);
      }
      // Stream unchanged: no truncation, reserialization, cookies or backend auth headers.
      return new Response(response.body, {
        status: response.status,
        headers: { "Content-Type": contentType, "Cache-Control": "no-store" },
      });
    } catch {
      return error(id, -32603, "Backend unreachable; check HTTPS connectivity", 502);
    }
  },
};
