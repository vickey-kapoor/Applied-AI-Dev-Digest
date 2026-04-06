import { NextRequest, NextResponse } from "next/server";
import { getRedis } from "@/lib/kv";
import { TOPICS, getDefaultTopicConfig, type TopicConfig } from "@/lib/topics";
import { requireAuth, requireJson, rateLimit } from "@/lib/auth";

const KV_KEY = "topics:config";
const KV_CUSTOM_KEYWORDS = "topics:custom_keywords";
const VALID_IDS = new Set(TOPICS.map((t) => t.id));
const MAX_CUSTOM_KEYWORDS_PER_TOPIC = 20;
const MAX_KEYWORD_LENGTH = 100;

export type CustomKeywordsMap = Record<string, string[]>;

export async function GET() {
  const result: { config: TopicConfig; customKeywords: CustomKeywordsMap } = {
    config: getDefaultTopicConfig(),
    customKeywords: {},
  };

  try {
    const redis = getRedis();
    if (redis) {
      const [config, custom] = await Promise.all([
        redis.get<TopicConfig>(KV_KEY),
        redis.get<CustomKeywordsMap>(KV_CUSTOM_KEYWORDS),
      ]);
      if (config) result.config = config;
      if (custom) result.customKeywords = custom;
    }
  } catch (e) {
    console.error("[TOPICS] KV read failed, returning defaults:", e);
  }
  return NextResponse.json(result);
}

export async function POST(request: NextRequest) {
  const authError = requireAuth(request);
  if (authError) return authError;

  const rateLimitError = await rateLimit(request);
  if (rateLimitError) return rateLimitError;

  const jsonError = requireJson(request);
  if (jsonError) return jsonError;

  let body: { config: TopicConfig; customKeywords?: CustomKeywordsMap };
  try {
    body = await request.json();
  } catch {
    return NextResponse.json({ error: "Invalid JSON" }, { status: 400 });
  }

  // Validate config
  for (const [key, value] of Object.entries(body.config)) {
    if (!VALID_IDS.has(key)) {
      return NextResponse.json({ error: `Unknown topic: ${key}` }, { status: 400 });
    }
    if (typeof value !== "boolean") {
      return NextResponse.json({ error: `Invalid value for ${key}` }, { status: 400 });
    }
  }

  // Validate custom keywords if provided
  if (body.customKeywords) {
    for (const [key, value] of Object.entries(body.customKeywords)) {
      if (!VALID_IDS.has(key)) {
        return NextResponse.json({ error: `Unknown topic for custom keywords: ${key}` }, { status: 400 });
      }
      if (!Array.isArray(value) || !value.every((v) => typeof v === "string")) {
        return NextResponse.json({ error: `Invalid custom keywords for ${key}` }, { status: 400 });
      }
      if (value.length > MAX_CUSTOM_KEYWORDS_PER_TOPIC) {
        return NextResponse.json({ error: `Too many custom keywords for ${key}` }, { status: 400 });
      }
      if (value.some((v) => v.length > MAX_KEYWORD_LENGTH)) {
        return NextResponse.json({ error: `Keyword too long in ${key}` }, { status: 400 });
      }
    }
  }

  const redis = getRedis();
  if (!redis) {
    return NextResponse.json({ error: "KV not configured" }, { status: 503 });
  }

  try {
    await redis.set(KV_KEY, body.config);
    if (body.customKeywords) {
      await redis.set(KV_CUSTOM_KEYWORDS, body.customKeywords);
    }
    return NextResponse.json({ config: body.config, customKeywords: body.customKeywords || {} });
  } catch (e) {
    console.error("[TOPICS] KV write failed:", e);
    return NextResponse.json({ error: "Failed to save" }, { status: 500 });
  }
}
