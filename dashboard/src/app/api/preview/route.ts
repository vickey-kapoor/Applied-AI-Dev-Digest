import { NextResponse } from "next/server";
import { getRedis } from "@/lib/kv";

const KV_KEY = "digest:last";

export async function GET() {
  const redis = getRedis();
  if (!redis) {
    return NextResponse.json({ error: "KV not configured" }, { status: 503 });
  }

  try {
    const paper = await redis.get(KV_KEY);
    if (!paper) {
      return NextResponse.json(
        { error: "No digest sent yet \u2014 trigger a manual run first" },
        { status: 404 }
      );
    }
    return NextResponse.json(paper);
  } catch (e) {
    console.error("[PREVIEW] KV read failed:", e);
    return NextResponse.json({ error: "Failed to read from KV" }, { status: 500 });
  }
}
