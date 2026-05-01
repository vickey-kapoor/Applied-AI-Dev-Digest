"use client";

import { useState, useCallback } from "react";
import { Card, CardContent } from "@/components/ui/card";
import { Eye, RefreshCw, Send, Loader2, Check, AlertCircle } from "lucide-react";

interface PreviewPaper {
  title: string;
  source: string;
  url: string;
  type: string;
  topic_id?: string;
  summary: string;
  claim: string;
  evidence: string;
  method: string;
  limitations: string;
  safety_relevance: string;
  rigor: string;
  date: string;
}

type FetchStatus = "idle" | "loading" | "done" | "error";
type SendStatus = "idle" | "sending" | "sent" | "error";

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
    <div className="py-8">
      <div className="mb-8">
        <div className="flex items-baseline gap-3 mb-1">
          <Eye className="h-7 w-7 text-primary shrink-0 self-center" />
          <h1 className="text-2xl font-display font-bold text-foreground">
            Digest Preview
          </h1>
        </div>
        <p className="text-muted-foreground mt-1">
          View the last digest the pipeline sent to Telegram.
        </p>
      </div>

      {/* Load button */}
      {fetchStatus !== "loading" && (
        <button
          onClick={fetchPreview}
          className="mb-6 inline-flex items-center gap-2 px-5 py-2.5 bg-primary text-white text-sm font-medium rounded-lg hover:bg-primary/80 transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
        >
          <RefreshCw className="h-4 w-4" />
          {paper ? "Refresh" : "Load last digest"}
        </button>
      )}

      {/* Loading state */}
      {fetchStatus === "loading" && (
        <Card className="mb-6">
          <CardContent className="flex flex-col items-center justify-center py-16">
            <Loader2 className="h-8 w-8 text-primary animate-spin mb-4" />
            <p className="text-foreground font-medium">Loading last digest...</p>
          </CardContent>
        </Card>
      )}

      {/* Error state */}
      {fetchStatus === "error" && (
        <Card className="mb-6 border-red-200 dark:border-red-800" role="alert">
          <CardContent className="flex items-center gap-3 py-4">
            <AlertCircle className="h-5 w-5 text-red-500 shrink-0" />
            <div>
              <p className="text-sm font-medium text-red-700 dark:text-red-400">{fetchError}</p>
              <p className="text-xs text-muted-foreground mt-0.5">Trigger a manual workflow run to generate a digest first.</p>
            </div>
          </CardContent>
        </Card>
      )}

      {/* Preview card — Telegram message mockup */}
      {paper && fetchStatus === "done" && (
        <>
          <div className="rounded-2xl border border-border bg-card p-1 mb-6 shadow-xl">
            {/* Phone-frame header */}
            <div className="flex items-center gap-2 px-4 py-2 border-b border-border">
              <div className="h-2.5 w-2.5 rounded-full bg-primary" />
              <span className="text-xs text-muted-foreground font-mono">Telegram Preview</span>
              {paper.date && (
                <span className="text-xs text-muted-foreground/50 font-mono ml-auto">{paper.date}</span>
              )}
            </div>
            {/* Message bubble */}
            <div className="p-4">
              <div className="bg-background rounded-xl p-4 max-w-md font-mono text-sm leading-relaxed text-foreground space-y-3">
                <p className="text-muted-foreground/70">
                  {typeTag} · {paper.source}
                  {paper.rigor && <span> · {paper.rigor}</span>}
                </p>
                <p className="font-bold text-foreground">{paper.title}</p>
                {paper.claim && (
                  <>
                    <p className="font-bold text-foreground text-xs uppercase tracking-wide">Claim</p>
                    <p className="text-muted-foreground">{paper.claim}</p>
                  </>
                )}
                {paper.evidence && (
                  <>
                    <p className="font-bold text-foreground text-xs uppercase tracking-wide">Evidence</p>
                    <p className="text-muted-foreground">{paper.evidence}</p>
                  </>
                )}
                {paper.method && (
                  <>
                    <p className="font-bold text-foreground text-xs uppercase tracking-wide">Method</p>
                    <p className="text-muted-foreground">{paper.method}</p>
                  </>
                )}
                {paper.limitations && (
                  <>
                    <p className="font-bold text-foreground text-xs uppercase tracking-wide">Limitations</p>
                    <p className="text-muted-foreground">{paper.limitations}</p>
                  </>
                )}
                {paper.safety_relevance && (
                  <>
                    <p className="font-bold text-foreground text-xs uppercase tracking-wide">Safety relevance</p>
                    <p className="text-muted-foreground">{paper.safety_relevance}</p>
                  </>
                )}
                {!paper.claim && paper.summary && (
                  <p className="text-muted-foreground">{paper.summary}</p>
                )}
                {paper.url && (
                  <p className="text-primary break-all">{paper.url}</p>
                )}
              </div>
            </div>
          </div>

          {/* Action buttons */}
          <div className="flex items-center gap-3">
            <button
              onClick={sendToTelegram}
              disabled={sendStatus === "sending" || sendStatus === "sent"}
              className={`inline-flex items-center gap-2 px-5 py-2.5 text-sm font-medium rounded-lg transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring ${
                sendStatus === "sent"
                  ? "bg-green-600 dark:bg-green-700 text-white"
                  : "bg-primary text-white hover:bg-primary/80 disabled:opacity-50"
              }`}
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
            <button
              onClick={fetchPreview}
              className="inline-flex items-center gap-2 px-5 py-2.5 text-sm font-medium rounded-lg border border-border text-muted-foreground hover:bg-muted hover:text-foreground transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
            >
              <RefreshCw className="h-4 w-4" />
              Refresh
            </button>
            {sendStatus === "error" && (
              <span role="alert" className="text-sm text-red-600 dark:text-red-400 flex items-center gap-1">
                <AlertCircle className="h-4 w-4" />
                {sendError}
              </span>
            )}
          </div>
        </>
      )}

      {/* Idle state */}
      {fetchStatus === "idle" && !paper && (
        <Card>
          <CardContent className="flex flex-col items-center justify-center py-16 text-center">
            <Eye className="h-12 w-12 text-muted-foreground/40 mb-4" />
            <p className="text-muted-foreground font-medium">No preview loaded yet</p>
            <p className="text-sm text-muted-foreground/70 mt-1">
              Click the button above to load the last digest sent by the pipeline.
            </p>
          </CardContent>
        </Card>
      )}
    </div>
  );
}
