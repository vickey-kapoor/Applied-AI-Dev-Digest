import { NextRequest, NextResponse } from "next/server";
import { getRedis } from "@/lib/kv";
import { requireAuth, requireJson, isValidUrl, rateLimit } from "@/lib/auth";

const KV_KEY = "feedback:log";
const MAX_ENTRIES = 90;

interface FeedbackEntry {
  url: string;
  rating: 1 | -1;
  topic_id: string;
  date: string;
}

export async function POST(request: NextRequest) {
  const authError = requireAuth(request);
  if (authError) return authError;

  const rateLimitError = await rateLimit(request);
  if (rateLimitError) return rateLimitError;

  const jsonError = requireJson(request);
  if (jsonError) return jsonError;

  let body: FeedbackEntry;
  try {
    body = await request.json();
  } catch {
    return NextResponse.json({ error: "Invalid JSON" }, { status: 400 });
  }

  if (!body.url || !body.date || ![1, -1].includes(body.rating)) {
    return NextResponse.json({ error: "Missing or invalid fields" }, { status: 400 });
  }

  if (!isValidUrl(body.url)) {
    return NextResponse.json({ error: "Invalid URL" }, { status: 400 });
  }

  // Sanitize topic_id — only allow known alphanumeric IDs
  if (body.topic_id && !/^[a-z0-9_-]{1,50}$/i.test(body.topic_id)) {
    return NextResponse.json({ error: "Invalid topic_id" }, { status: 400 });
  }

  // Sanitize date — only allow ISO-like date strings
  if (!/^\d{4}-\d{2}-\d{2}/.test(body.date)) {
    return NextResponse.json({ error: "Invalid date format" }, { status: 400 });
  }

  const redis = getRedis();
  if (!redis) {
    return NextResponse.json({ error: "KV not configured" }, { status: 503 });
  }

  try {
    await redis.rpush(KV_KEY, JSON.stringify(body));
    // Trim to cap at MAX_ENTRIES (drop oldest)
    await redis.ltrim(KV_KEY, -MAX_ENTRIES, -1);
    return NextResponse.json({ ok: true });
  } catch (e) {
    console.error("[FEEDBACK] KV write failed:", e);
    return NextResponse.json({ error: "Failed to save" }, { status: 500 });
  }
}
