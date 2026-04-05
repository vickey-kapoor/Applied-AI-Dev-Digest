import { NextResponse } from "next/server";
import { getRedis } from "@/lib/kv";
import { TOPICS } from "@/lib/topics";

const KV_KEY = "stats:topics";

export async function GET() {
  let counts: Record<string, number> = {};
  try {
    const redis = getRedis();
    if (redis) {
      const raw = await redis.get<Record<string, number>>(KV_KEY);
      if (raw) counts = raw;
    }
  } catch (e) {
    console.error("[STATS] KV read failed:", e);
  }

  const total = Object.values(counts).reduce((s, n) => s + n, 0);

  const stats = TOPICS.map((topic) => ({
    id: topic.id,
    name: topic.name,
    category: topic.category,
    wins: counts[topic.id] || 0,
    pct: total > 0 ? Math.round(((counts[topic.id] || 0) / total) * 100) : 0,
  }));

  // Sort by wins descending
  stats.sort((a, b) => b.wins - a.wins);

  return NextResponse.json({ stats, total });
}
