import { NextRequest, NextResponse } from "next/server";
import { createHmac, timingSafeEqual } from "node:crypto";
import { Ratelimit } from "@upstash/ratelimit";
import { getRedis } from "@/lib/kv";

/** Cookie carrying proof of a dashboard login — set by POST /api/login. */
export const SESSION_COOKIE = "dashboard_auth";

/**
 * Constant-time string comparison. Avoids leaking, through response timing,
 * how many leading characters of a guessed secret are correct. The length
 * branch still runs a dummy compare so timing does not reveal the length
 * either.
 */
export function safeEqual(a: string, b: string): boolean {
  const ab = Buffer.from(a);
  const bb = Buffer.from(b);
  if (ab.length !== bb.length) {
    timingSafeEqual(ab, ab);
    return false;
  }
  return timingSafeEqual(ab, bb);
}

/**
 * The value stored in the session cookie: an HMAC of the secret, not the
 * secret itself. So a leaked cookie (a proxy log, say) cannot be replayed as
 * the Bearer token that API clients use.
 */
export function sessionToken(secret: string): string {
  return createHmac("sha256", secret).update("dashboard-session-v1").digest("hex");
}

/**
 * Gate a mutating request.
 *
 * Two accepted credentials:
 *   - `Authorization: Bearer <DASHBOARD_API_SECRET>` for non-browser clients.
 *     A header, not a cookie, so CSRF cannot reach it.
 *   - The `dashboard_auth` session cookie (httpOnly, SameSite=Strict) set by
 *     /api/login, for the dashboard UI. SameSite=Strict means the browser
 *     never sends it on a cross-site request, which is what defends these
 *     writes against CSRF.
 *
 * This replaces the previous "same-origin Origin/Referer is sufficient" path.
 * `Origin` is set freely by any non-browser client, so it could never
 * authenticate — it only looked like a check. It is kept here solely as a
 * defence-in-depth check layered on top of the cookie, never as a credential
 * on its own.
 *
 * When no secret is configured the endpoints are open only outside
 * production (a local-dev convenience). In production a missing secret is a
 * misconfiguration and fails closed rather than exposing every mutating
 * endpoint to the internet.
 */
export function requireAuth(request: NextRequest): NextResponse | null {
  const unauthorized = () =>
    NextResponse.json({ error: "Unauthorized" }, { status: 401 });

  const secret = process.env.DASHBOARD_API_SECRET;
  if (!secret) {
    return process.env.NODE_ENV === "production" ? unauthorized() : null;
  }

  // Non-browser clients: Bearer token.
  const auth = request.headers.get("authorization");
  if (auth?.startsWith("Bearer ") && safeEqual(auth.slice(7), secret)) {
    return null;
  }

  // Browser clients: the session cookie, plus a same-origin check as an
  // extra layer (the cookie's SameSite=Strict is the real CSRF defence).
  const cookie = request.cookies.get(SESSION_COOKIE)?.value;
  if (cookie && safeEqual(cookie, sessionToken(secret))) {
    const origin = request.headers.get("origin");
    const referer = request.headers.get("referer");
    const host = request.headers.get("host");
    if ((origin || referer) && host) {
      const reqOrigin = (origin || new URL(referer!).origin).toLowerCase();
      const h = host.toLowerCase();
      if (reqOrigin !== `https://${h}` && reqOrigin !== `http://${h}`) {
        return unauthorized(); // cookie presented on a cross-site request
      }
    }
    return null;
  }

  return unauthorized();
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
let _ratelimit: Ratelimit | null | undefined;

function getRatelimit(): Ratelimit | null {
  if (_ratelimit !== undefined) return _ratelimit;
  const redis = getRedis();
  if (!redis) {
    _ratelimit = null;
    return null;
  }
  _ratelimit = new Ratelimit({
    redis,
    limiter: Ratelimit.slidingWindow(20, "1 m"), // 20 requests per minute
    prefix: "ratelimit:api",
  });
  return _ratelimit;
}

/**
 * Rate-limit requests by IP. Returns 429 if limit exceeded.
 * No-ops if Redis is not configured.
 */
export async function rateLimit(request: NextRequest): Promise<NextResponse | null> {
  const limiter = getRatelimit();
  if (!limiter) return null; // No Redis — skip rate limiting

  const ip = request.headers.get("x-forwarded-for")?.split(",")[0]?.trim()
    || request.headers.get("x-real-ip")
    || "unknown";

  const { success, remaining } = await limiter.limit(ip);
  if (!success) {
    return NextResponse.json(
      { error: "Too many requests" },
      { status: 429, headers: { "X-RateLimit-Remaining": String(remaining) } }
    );
  }
  return null;
}

export function isValidUrl(url: string): boolean {
  if (!url || typeof url !== "string") return false;
  try {
    const parsed = new URL(url);
    return ["http:", "https:"].includes(parsed.protocol);
  } catch {
    return false;
  }
}
