import { NextRequest, NextResponse } from "next/server";
import {
  requireJson,
  rateLimit,
  safeEqual,
  sessionToken,
  SESSION_COOKIE,
} from "@/lib/auth";

// Exchanges the dashboard secret for a session cookie. The cookie is what the
// UI then presents on its mutating calls (see requireAuth), so the secret
// itself is entered once and never lives in client-side JavaScript.
export async function POST(request: NextRequest) {
  const rateLimitError = await rateLimit(request);
  if (rateLimitError) return rateLimitError;

  const jsonError = requireJson(request);
  if (jsonError) return jsonError;

  const secret = process.env.DASHBOARD_API_SECRET;
  if (!secret) {
    // No secret configured — there is nothing to log in against. Outside
    // production the endpoints are already open; in production this is a
    // misconfiguration.
    return NextResponse.json({ error: "Login is not enabled" }, { status: 503 });
  }

  let body: { secret?: string };
  try {
    body = await request.json();
  } catch {
    return NextResponse.json({ error: "Invalid JSON" }, { status: 400 });
  }

  if (typeof body.secret !== "string" || !safeEqual(body.secret, secret)) {
    return NextResponse.json({ error: "Invalid secret" }, { status: 401 });
  }

  const res = NextResponse.json({ ok: true });
  res.cookies.set(SESSION_COOKIE, sessionToken(secret), {
    httpOnly: true,
    secure: process.env.NODE_ENV === "production",
    sameSite: "strict",
    path: "/",
    maxAge: 60 * 60 * 24 * 30, // 30 days
  });
  return res;
}

// Clears the session cookie.
export async function DELETE() {
  const res = NextResponse.json({ ok: true });
  res.cookies.set(SESSION_COOKIE, "", {
    httpOnly: true,
    secure: process.env.NODE_ENV === "production",
    sameSite: "strict",
    path: "/",
    maxAge: 0,
  });
  return res;
}
