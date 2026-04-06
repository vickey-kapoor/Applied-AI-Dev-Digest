import { NextRequest, NextResponse } from "next/server";
import { getRedis } from "@/lib/kv";
import { requireAuth } from "@/lib/auth";

const KV_KEY = "digest:last";

interface LastPaper {
  title: string;
  authors: string;
  source: string;
  url: string;
  summary: string;
  date: string;
}

function escapeMarkdown(text: string): string {
  return text.replace(/([_*\[\]()~`>#+\-=|{}.!\\])/g, "\\$1");
}

function formatTelegramMessage(paper: LastPaper): string {
  const title = escapeMarkdown(paper.title || "Untitled");
  const source = escapeMarkdown(paper.source || "Unknown");
  const summary = escapeMarkdown(paper.summary || "");
  const url = paper.url || "";

  return `*Daily AI Dev Digest*\n\n*${title}*\n\n${summary}\n\n${url}\n_Lab: ${source}_`;
}

export async function POST(request: NextRequest) {
  const authError = requireAuth(request);
  if (authError) return authError;

  const redis = getRedis();
  if (!redis) {
    return NextResponse.json({ error: "KV not configured" }, { status: 503 });
  }

  let paper: LastPaper | null = null;
  try {
    paper = await redis.get<LastPaper>(KV_KEY);
  } catch (e) {
    console.error("[TEST-SEND] KV read failed:", e);
    return NextResponse.json({ error: "Failed to read from KV" }, { status: 500 });
  }

  if (!paper) {
    return NextResponse.json({ error: "No papers sent yet this week" }, { status: 404 });
  }

  const botToken = process.env.TELEGRAM_BOT_TOKEN;
  const chatId = process.env.TELEGRAM_CHAT_ID;
  if (!botToken || !chatId) {
    return NextResponse.json(
      { error: "Telegram service not configured" },
      { status: 503 }
    );
  }

  const message = formatTelegramMessage(paper);

  try {
    const res = await fetch(`https://api.telegram.org/bot${botToken}/sendMessage`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        chat_id: chatId,
        text: message,
        parse_mode: "Markdown",
        disable_web_page_preview: false,
      }),
    });

    const data = await res.json();
    if (!data.ok) {
      console.error("[TEST-SEND] Telegram error:", data.description);
      return NextResponse.json({ error: `Telegram: ${data.description || "send failed"}` }, { status: 502 });
    }

    return NextResponse.json({ ok: true, title: paper.title });
  } catch (e) {
    console.error("[TEST-SEND] Telegram request failed:", e);
    return NextResponse.json({ error: "Failed to send Telegram message" }, { status: 502 });
  }
}
