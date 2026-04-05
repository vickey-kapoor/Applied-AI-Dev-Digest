import { NextRequest, NextResponse } from "next/server";
import { getRedis } from "@/lib/kv";

const KV_KEY = "digest:paused";

export async function GET() {
  try {
    const redis = getRedis();
    if (redis) {
      const paused = await redis.get<boolean>(KV_KEY);
      return NextResponse.json({ paused: !!paused });
    }
  } catch (e) {
    console.error("[PAUSE] KV read failed:", e);
  }
  return NextResponse.json({ paused: false });
}

export async function POST(request: NextRequest) {
  let body: { paused: boolean };
  try {
    body = await request.json();
  } catch {
    return NextResponse.json({ error: "Invalid JSON" }, { status: 400 });
  }

  if (typeof body.paused !== "boolean") {
    return NextResponse.json({ error: "paused must be boolean" }, { status: 400 });
  }

  const redis = getRedis();
  if (!redis) {
    return NextResponse.json({ error: "KV not configured" }, { status: 503 });
  }

  try {
    await redis.set(KV_KEY, body.paused);
    return NextResponse.json({ paused: body.paused });
  } catch (e) {
    console.error("[PAUSE] KV write failed:", e);
    return NextResponse.json({ error: "Failed to save" }, { status: 500 });
  }
}
