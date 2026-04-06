import { NextRequest, NextResponse } from "next/server";

/**
 * Validate that the request carries a valid API secret.
 *
 * Checks the Authorization header for a Bearer token matching
 * DASHBOARD_API_SECRET. If the env var is not set, all requests
 * are allowed (open mode for local dev).
 */
export function requireAuth(request: NextRequest): NextResponse | null {
  const secret = process.env.DASHBOARD_API_SECRET;
  if (!secret) {
    // No secret configured — allow all (local dev / open mode)
    return null;
  }

  const auth = request.headers.get("authorization");
  if (auth === `Bearer ${secret}`) {
    return null; // Authorized
  }

  // Check origin for same-origin browser requests (CSRF protection)
  const origin = request.headers.get("origin");
  const referer = request.headers.get("referer");
  const host = request.headers.get("host");

  if (host && (origin || referer)) {
    const requestOrigin = (origin || new URL(referer!).origin).toLowerCase();
    const hostLower = host.toLowerCase();
    if (requestOrigin === `https://${hostLower}` || requestOrigin === `http://${hostLower}`) {
      return null; // Same-origin browser request — allow
    }
  }

  // No origin/referer = non-browser request without Bearer token
  if (!origin && !referer && !auth) {
    return NextResponse.json({ error: "Unauthorized" }, { status: 401 });
  }

  return NextResponse.json({ error: "Unauthorized" }, { status: 401 });
}

/**
 * Validate that Content-Type is application/json for POST requests.
 */
export function requireJson(request: NextRequest): NextResponse | null {
  const ct = request.headers.get("content-type");
  if (!ct?.includes("application/json")) {
    return NextResponse.json(
      { error: "Content-Type must be application/json" },
      { status: 415 }
    );
  }
  return null;
}

/**
 * Validate that a URL is safe (http/https only, no javascript/data URIs).
 */
export function isValidUrl(url: string): boolean {
  if (!url || typeof url !== "string") return false;
  try {
    const parsed = new URL(url);
    return ["http:", "https:"].includes(parsed.protocol);
  } catch {
    return false;
  }
}
