import { NextResponse } from "next/server";
import { getRedis } from "@/lib/kv";

const KV_KEY = "digest:weekly";

export interface HistoryEntry {
  title: string;
  authors: string;
  institution?: string;
  topic_id?: string;
  url: string;
  claim: string;
  safety_relevance?: string;
  rigor?: string;
  date: string;
}

export async function GET() {
  try {
    const redis = getRedis();
    if (redis) {
      const raw = await redis.lrange(KV_KEY, 0, -1);
      const entries: HistoryEntry[] = [];
      for (const item of raw) {
        if (typeof item === "string") {
          try { entries.push(JSON.parse(item)); } catch { /* skip */ }
        } else if (item && typeof item === "object") {
          entries.push(item as HistoryEntry);
        }
      }
      // Most recent first
      entries.sort((a, b) => (b.date || "").localeCompare(a.date || ""));
      return NextResponse.json({ entries });
    }
  } catch (e) {
    console.error("[HISTORY] KV read failed:", e);
  }
  return NextResponse.json({ entries: [] });
}
