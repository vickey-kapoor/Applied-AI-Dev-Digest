import { NextRequest, NextResponse } from "next/server";
import { requireAuth, requireJson, isValidUrl, rateLimit } from "@/lib/auth";

function escapeMarkdown(text: string): string {
  return text.replace(/([_*\[\]()~`>#+\-=|{}.!\\])/g, "\\$1");
}

export async function POST(request: NextRequest) {
  const authError = requireAuth(request);
  if (authError) return authError;

  const rateLimitError = await rateLimit(request);
  if (rateLimitError) return rateLimitError;

  const jsonError = requireJson(request);
  if (jsonError) return jsonError;

  let body: { title: string; source: string; summary: string; url: string };
  try {
    body = await request.json();
  } catch {
    return NextResponse.json({ error: "Invalid JSON" }, { status: 400 });
  }

  if (body.url && !isValidUrl(body.url)) {
    return NextResponse.json({ error: "Invalid URL" }, { status: 400 });
  }

  const botToken = process.env.TELEGRAM_BOT_TOKEN;
  const chatId = process.env.TELEGRAM_CHAT_ID;
  if (!botToken || !chatId) {
    return NextResponse.json({ error: "Telegram service not configured" }, { status: 503 });
  }

  const title = escapeMarkdown(body.title || "Untitled");
  const source = escapeMarkdown(body.source || "Unknown");
  const summary = escapeMarkdown(body.summary || "");
  const message = `*Daily AI Dev Digest*\n\n*${title}*\n\n${summary}\n\n${body.url || ""}\n_Lab: ${source}_`;

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
      return NextResponse.json({ error: `Telegram: ${data.description}` }, { status: 502 });
    }

    return NextResponse.json({ ok: true, title: body.title });
  } catch (e) {
    console.error("[PREVIEW-SEND] failed:", e);
    return NextResponse.json({ error: "Failed to send" }, { status: 502 });
  }
}
