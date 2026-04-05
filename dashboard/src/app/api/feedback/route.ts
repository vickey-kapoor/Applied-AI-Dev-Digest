import { NextRequest, NextResponse } from "next/server";
import { getRedis } from "@/lib/kv";

const KV_KEY = "feedback:log";
const MAX_ENTRIES = 90;

interface FeedbackEntry {
  url: string;
  rating: 1 | -1;
  topic_id: string;
  date: string;
}

export async function POST(request: NextRequest) {
  let body: FeedbackEntry;
  try {
    body = await request.json();
  } catch {
    return NextResponse.json({ error: "Invalid JSON" }, { status: 400 });
  }

  if (!body.url || !body.date || ![1, -1].includes(body.rating)) {
    return NextResponse.json({ error: "Missing or invalid fields" }, { status: 400 });
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
