import { describe, it, expect, afterEach, vi } from "vitest";
import { NextRequest } from "next/server";
import { requireAuth, sessionToken, SESSION_COOKIE } from "@/lib/auth";

const HOST = "dash.example.com";
const SECRET = "s3cr3t-value";

function req(headers: Record<string, string>): NextRequest {
  return new NextRequest(`https://${HOST}/api/pause`, {
    method: "POST",
    headers: { host: HOST, ...headers },
  });
}

afterEach(() => {
  vi.unstubAllEnvs();
});

describe("requireAuth", () => {
  it("allows a request with the correct Bearer token", () => {
    vi.stubEnv("DASHBOARD_API_SECRET", SECRET);
    expect(requireAuth(req({ authorization: `Bearer ${SECRET}` }))).toBeNull();
  });

  it("rejects a wrong Bearer token", () => {
    vi.stubEnv("DASHBOARD_API_SECRET", SECRET);
    expect(requireAuth(req({ authorization: "Bearer nope" }))?.status).toBe(401);
  });

  it("allows a request carrying the session cookie", () => {
    vi.stubEnv("DASHBOARD_API_SECRET", SECRET);
    const cookie = `${SESSION_COOKIE}=${sessionToken(SECRET)}`;
    expect(requireAuth(req({ cookie, origin: `https://${HOST}` }))).toBeNull();
  });

  it("rejects a forged Origin with no credential (the old bypass)", () => {
    vi.stubEnv("DASHBOARD_API_SECRET", SECRET);
    expect(requireAuth(req({ origin: `https://${HOST}` }))?.status).toBe(401);
    expect(requireAuth(req({ referer: `https://${HOST}/x` }))?.status).toBe(401);
  });

  it("rejects the session cookie when presented cross-site", () => {
    vi.stubEnv("DASHBOARD_API_SECRET", SECRET);
    const cookie = `${SESSION_COOKIE}=${sessionToken(SECRET)}`;
    expect(requireAuth(req({ cookie, origin: "https://evil.example" }))?.status).toBe(401);
  });

  it("rejects a cookie holding the raw secret instead of the token", () => {
    vi.stubEnv("DASHBOARD_API_SECRET", SECRET);
    const cookie = `${SESSION_COOKIE}=${SECRET}`;
    expect(requireAuth(req({ cookie }))?.status).toBe(401);
  });

  it("fails closed in production when no secret is configured", () => {
    vi.stubEnv("DASHBOARD_API_SECRET", "");
    vi.stubEnv("NODE_ENV", "production");
    expect(requireAuth(req({}))?.status).toBe(401);
  });

  it("allows open mode outside production when no secret is configured", () => {
    vi.stubEnv("DASHBOARD_API_SECRET", "");
    vi.stubEnv("NODE_ENV", "development");
    expect(requireAuth(req({}))).toBeNull();
  });
});
