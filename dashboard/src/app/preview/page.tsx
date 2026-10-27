"use client";

import { useState, useCallback } from "react";
import { Card, CardContent } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { PageHeader } from "@/components/ui/page-header";
import { EmptyState } from "@/components/ui/empty-state";
import { buttonVariants } from "@/components/ui/button";
import { cn } from "@/lib/utils";
import { Eye, RefreshCw, Send, Loader2, Check, AlertCircle } from "lucide-react";

interface PreviewPaper {
  title: string;
  source: string;
  url: string;
  type: string;
  topic_id?: string;
  summary: string;
  what_shipped: string;
  capabilities: string;
  availability: string;
  why_it_matters: string;
  caveats: string;
  release_type: string;
  date: string;
}

type FetchStatus = "idle" | "loading" | "done" | "error";
type SendStatus = "idle" | "sending" | "sent" | "error";

/** The digest's message sections, in the order Telegram receives them. */
const SECTIONS: { key: keyof PreviewPaper; label: string }[] = [
  { key: "what_shipped", label: "What shipped" },
  { key: "capabilities", label: "Capabilities" },
  { key: "availability", label: "Availability" },
  { key: "why_it_matters", label: "Why it matters" },
  { key: "caveats", label: "Caveats" },
];

export default function PreviewPage() {
  const [paper, setPaper] = useState<PreviewPaper | null>(null);
  const [fetchStatus, setFetchStatus] = useState<FetchStatus>("idle");
  const [fetchError, setFetchError] = useState("");
  const [sendStatus, setSendStatus] = useState<SendStatus>("idle");
  const [sendError, setSendError] = useState("");

  const fetchPreview = useCallback(async () => {
    setFetchStatus("loading");
    setFetchError("");
    setPaper(null);
    try {
      const res = await fetch("/api/preview");
      const data = await res.json();
      if (!res.ok || data.error) {
        setFetchStatus("error");
        setFetchError(data.error || "Failed to load digest");
        return;
      }
      setPaper(data);
      setFetchStatus("done");
      setSendStatus("idle");
    } catch {
      setFetchStatus("error");
      setFetchError("Network error");
    }
  }, []);

  const sendToTelegram = useCallback(async () => {
    if (!paper) return;
    setSendStatus("sending");
    setSendError("");
    try {
      const res = await fetch("/api/preview/send", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(paper),
      });
      const data = await res.json();
      if (!res.ok) {
        setSendStatus("error");
        setSendError(data.error || "Send failed");
        setTimeout(() => setSendStatus("idle"), 4000);
        return;
      }
      setSendStatus("sent");
    } catch {
      setSendStatus("error");
      setSendError("Network error");
      setTimeout(() => setSendStatus("idle"), 4000);
    }
  }, [paper]);

  const typeTag =
    paper?.type === "release"
      ? "#Release"
      : paper?.type === "discussion"
        ? "#Discussion"
        : paper?.type === "paper"
          ? "#Paper"
          : "#Announcement";

  return (
    <div className="pb-20">
      <PageHeader
        eyebrow="Delivery"
        title="Digest Preview"
        description="The last digest the pipeline sent to Telegram, rendered exactly as it arrives."
        icon={Eye}
        actions={
          fetchStatus !== "loading" ? (
            <button
              onClick={fetchPreview}
              className={cn(
                buttonVariants({
                  variant: paper ? "secondary" : "primary",
                  size: "lg",
                }),
              )}
            >
              <RefreshCw className="h-4 w-4" />
              {paper ? "Refresh" : "Load last digest"}
            </button>
          ) : (
            <span
              className={cn(
                buttonVariants({ variant: "secondary", size: "lg" }),
                "pointer-events-none",
              )}
            >
              <Loader2 className="h-4 w-4 animate-spin" />
              Loading
            </span>
          )
        }
      />

      {/* Loading state */}
      {fetchStatus === "loading" && (
        <Card elevation="flat" className="mt-8 bg-surface">
          <CardContent className="flex flex-col items-center justify-center py-20">
            <Loader2 className="mb-4 h-6 w-6 animate-spin text-primary" />
            <p className="text-sm text-muted-foreground">
              Loading the last digest…
            </p>
          </CardContent>
        </Card>
      )}

      {/* Error state */}
      {fetchStatus === "error" && (
        <Card
          className="mt-8 border-destructive/30 bg-destructive/5"
          role="alert"
        >
          <CardContent className="flex items-start gap-3 p-5">
            <AlertCircle className="mt-0.5 h-5 w-5 shrink-0 text-destructive" />
            <div>
              <p className="text-sm font-medium text-destructive">
                {fetchError}
              </p>
              <p className="mt-1 text-xs text-muted-foreground">
                Trigger a manual workflow run to generate a digest first.
              </p>
            </div>
          </CardContent>
        </Card>
      )}

      {/* Preview — Telegram message mockup */}
      {paper && fetchStatus === "done" && (
        <div className="mt-8 grid gap-6 lg:grid-cols-[minmax(0,1fr)_18rem] lg:items-start">
          <Card elevation="raised" className="overflow-hidden">
            {/* Chat header */}
            <div className="flex items-center gap-2.5 border-b border-border bg-surface px-4 py-3">
              <span className="flex h-6 w-6 items-center justify-center rounded-full bg-primary text-primary-foreground">
                <Send className="h-3 w-3" aria-hidden="true" />
              </span>
              <span className="text-xs font-medium text-foreground">
                Telegram
              </span>
              {paper.date && (
                <span className="ml-auto font-mono text-[0.6875rem] text-subtle-foreground">
                  {paper.date}
                </span>
              )}
            </div>

            {/* Message bubble */}
            <div className="bg-surface p-4 sm:p-6">
              <div className="surface-highlight max-w-xl rounded-xl rounded-tl-sm border border-border bg-card p-5 shadow-e2">
                <div className="flex flex-wrap items-center gap-2">
                  <Badge variant="accent" className="font-mono text-[0.6875rem]">
                    {typeTag}
                  </Badge>
                  <span className="text-xs font-medium text-foreground">
                    {paper.source}
                  </span>
                  {paper.release_type && (
                    <Badge
                      variant="outline"
                      className="font-mono text-[0.6875rem]"
                    >
                      {paper.release_type}
                    </Badge>
                  )}
                </div>

                <p className="mt-3 font-display text-base font-bold leading-snug text-foreground">
                  {paper.title}
                </p>

                <dl className="mt-4 space-y-3.5">
                  {SECTIONS.map(({ key, label }) => {
                    const value = paper[key];
                    if (!value) return null;
                    return (
                      <div key={key}>
                        <dt className="eyebrow">{label}</dt>
                        <dd className="mt-1 text-sm leading-relaxed text-muted-foreground">
                          {String(value)}
                        </dd>
                      </div>
                    );
                  })}
                  {!paper.what_shipped && paper.summary && (
                    <div>
                      <dd className="text-sm leading-relaxed text-muted-foreground">
                        {paper.summary}
                      </dd>
                    </div>
                  )}
                </dl>

                {paper.url && (
                  <a
                    href={paper.url}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="mt-4 block break-all border-t border-border pt-3 font-mono text-xs text-primary hover:underline"
                  >
                    {paper.url}
                  </a>
                )}
              </div>
            </div>
          </Card>

          {/* Actions rail */}
          <Card className="p-5 lg:sticky lg:top-24">
            <p className="eyebrow">Actions</p>
            <div className="mt-4 space-y-2.5">
              <button
                onClick={sendToTelegram}
                disabled={sendStatus === "sending" || sendStatus === "sent"}
                className={cn(
                  buttonVariants({
                    variant: sendStatus === "sent" ? "success" : "primary",
                    size: "lg",
                  }),
                  "w-full",
                )}
              >
                {sendStatus === "sending" ? (
                  <Loader2 className="h-4 w-4 animate-spin" />
                ) : sendStatus === "sent" ? (
                  <Check className="h-4 w-4" />
                ) : (
                  <Send className="h-4 w-4" />
                )}
                {sendStatus === "sent" ? "Sent to Telegram" : "Send to Telegram"}
              </button>
            </div>
            {sendStatus === "error" && (
              <p
                role="alert"
                className="mt-3 flex items-start gap-1.5 text-xs text-destructive"
              >
                <AlertCircle className="mt-px h-3.5 w-3.5 shrink-0" />
                {sendError}
              </p>
            )}
            <p className="mt-4 border-t border-border pt-4 text-xs leading-relaxed text-muted-foreground">
              Sending delivers this exact message to the configured Telegram
              chat.
            </p>
          </Card>
        </div>
      )}

      {/* Idle state */}
      {fetchStatus === "idle" && !paper && (
        <div className="mt-8">
          <EmptyState
            icon={Eye}
            title="No preview loaded"
            description="Load the last digest the pipeline sent to see it rendered as a Telegram message."
          >
            <button
              onClick={fetchPreview}
              className={cn(buttonVariants({ variant: "primary", size: "lg" }))}
            >
              <RefreshCw className="h-4 w-4" />
              Load last digest
            </button>
          </EmptyState>
        </div>
      )}
    </div>
  );
}
