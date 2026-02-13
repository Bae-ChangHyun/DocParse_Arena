import { NextRequest } from "next/server";

export const runtime = "edge";

const BACKEND_URL = process.env.BACKEND_URL || "http://localhost:8000";

const ALLOWED_PREFIXES = [
  "/api/battle",
  "/api/leaderboard",
  "/api/playground",
  "/api/documents",
  "/api/admin",
  "/api/health",
];

const STRIP_HEADERS = [
  "transfer-encoding",
  "content-length",
  "content-encoding",
  "access-control-allow-origin",
  "access-control-allow-methods",
  "access-control-allow-headers",
  "access-control-allow-credentials",
];

const SSE_HEADERS: Record<string, string> = {
  "Content-Type": "text/event-stream; charset=utf-8",
  "Cache-Control": "no-cache, no-transform",
  Connection: "keep-alive",
  "X-Accel-Buffering": "no",
};

function isSSE(response: Response): boolean {
  const ct = response.headers.get("content-type") || "";
  return ct.includes("text/event-stream");
}

async function handler(request: NextRequest) {
  const { pathname, search } = new URL(request.url);

  if (!ALLOWED_PREFIXES.some((prefix) => pathname.startsWith(prefix))) {
    return new Response(JSON.stringify({ error: "Not found" }), {
      status: 404,
      headers: { "Content-Type": "application/json" },
    });
  }

  const targetUrl = `${BACKEND_URL}${pathname}${search}`;

  try {
    const init: RequestInit = {
      method: request.method,
      headers: {
        "content-type": request.headers.get("content-type") || "",
        authorization: request.headers.get("authorization") || "",
      },
      cache: "no-store",
    };

    if (request.method !== "GET" && request.method !== "HEAD") {
      init.body = request.body;
      // @ts-expect-error duplex required for streaming request body
      init.duplex = "half";
    }

    const response = await fetch(targetUrl, init);

    const responseHeaders = new Headers(response.headers);
    for (const h of STRIP_HEADERS) {
      responseHeaders.delete(h);
    }

    if (isSSE(response)) {
      for (const [k, v] of Object.entries(SSE_HEADERS)) {
        responseHeaders.set(k, v);
      }
      return new Response(response.body, {
        status: response.status,
        headers: responseHeaders,
      });
    }

    return new Response(response.body, {
      status: response.status,
      statusText: response.statusText,
      headers: responseHeaders,
    });
  } catch {
    return new Response(JSON.stringify({ error: "Backend connection failed" }), {
      status: 502,
      headers: { "Content-Type": "application/json" },
    });
  }
}

export const GET = handler;
export const POST = handler;
export const PUT = handler;
export const DELETE = handler;
export const PATCH = handler;
