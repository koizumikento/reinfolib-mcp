// Test-only Dispatch identity simulation and loopback routing; never deploy this file.
import { createServer } from "node:http";
import { readFile } from "node:fs/promises";
const source = await readFile(new URL("../worker/index.js", import.meta.url), "utf8");
const { default: worker } = await import(`data:text/javascript;base64,${Buffer.from(source).toString("base64")}`);
const nativeFetch = globalThis.fetch;
globalThis.fetch = (url, options) => {
  if (url.href !== "https://backend.invalid/mcp") throw new Error("Unexpected backend");
  return nativeFetch(`http://127.0.0.1:${process.env.FIXTURE_BACKEND_PORT}/mcp`, options);
};
createServer(async (req, res) => {
  try {
    const chunks = [];
    for await (const chunk of req) chunks.push(chunk);
    const headers = new Headers(req.headers);
    headers.set("oai-authenticated-user-id", "synthetic-fixture-user");
    const request = new Request(`http://127.0.0.1:${process.env.FIXTURE_GATEWAY_PORT}${req.url}`, {
      method: req.method, headers,
      ...(req.method === "POST" ? { body: Buffer.concat(chunks) } : {}),
    });
    const response = await worker.fetch(request, {
      REINFOLIB_BACKEND_URL: "https://backend.invalid/mcp",
      REINFOLIB_BACKEND_TOKEN: process.env.REINFOLIB_BACKEND_TOKEN,
    });
    res.writeHead(response.status, Object.fromEntries(response.headers));
    if (response.body) for await (const chunk of response.body) res.write(chunk);
    res.end();
  } catch {
    res.writeHead(500); res.end("Fixture gateway failure");
  }
}).listen(Number(process.env.FIXTURE_GATEWAY_PORT), "127.0.0.1");
