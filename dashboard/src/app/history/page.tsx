"use client";

import { useState, useEffect, useCallback } from "react";
import { Card, CardContent } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { PageHeader } from "@/components/ui/page-header";
import { EmptyState } from "@/components/ui/empty-state";
import { TOPICS, CATEGORY_BADGE_COLORS } from "@/lib/topics";
import { cn } from "@/lib/utils";
import { Clock, ExternalLink, Inbox, ThumbsUp, ThumbsDown } from "lucide-react";
import { format, parseISO } from "date-fns";

interface HistoryEntry {
  title: string;
  // The digest writes the publishing lab as `source`; `authors` is legacy.
  source?: string;
  authors?: string;
  topic_id?: string;
  url: string;
  type?: string;
  what_shipped?: string;
  why_it_matters?: string;
  release_type?: string;
  date: string;
}

function getTopicBadge(topicId?: string) {
  if (!topicId) return null;
  const topic = TOPICS.find((t) => t.id === topicId);
  if (!topic) return null;
  return (
    <Badge
      variant="outline"
      className={cn("text-[0.6875rem]", CATEGORY_BADGE_COLORS[topic.category])}
    >
      {topic.name}
    </Badge>
  );
}

function formatDate(dateStr: string) {
  try {
    return format(parseISO(dateStr), "EEEE, MMM d");
  } catch {
    return dateStr;
  }
}

function getVotedUrls(): Record<string, 1 | -1> {
  if (typeof window === "undefined") return {};
  try {
    return JSON.parse(localStorage.getItem("feedback:votes") || "{}");
  } catch {
    return {};
  }
}

function setVotedUrl(url: string, rating: 1 | -1) {
  if (typeof window === "undefined") return;
  const votes = getVotedUrls();
  votes[url] = rating;
  localStorage.setItem("feedback:votes", JSON.stringify(votes));
}

export default function HistoryPage() {
  const [entries, setEntries] = useState<HistoryEntry[]>([]);
  const [loading, setLoading] = useState(true);
  const [votes, setVotes] = useState<Record<string, 1 | -1>>(getVotedUrls);

  useEffect(() => {
    fetch("/api/history")
      .then((r) => r.json())
      .then((d) => setEntries(d.entries || []))
      .catch(() => setEntries([]))
      .finally(() => setLoading(false));
  }, []);

  const submitFeedback = useCallback(async (entry: HistoryEntry, rating: 1 | -1) => {
    if (votes[entry.url]) return; // Already voted

    setVotes((prev) => ({ ...prev, [entry.url]: rating }));
    setVotedUrl(entry.url, rating);

    try {
      await fetch("/api/feedback", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          url: entry.url,
          rating,
          topic_id: entry.topic_id || "",
          date: entry.date,
        }),
      });
    } catch {
      // Vote already saved locally, KV failure is non-critical
    }
  }, [votes]);

  if (loading) {
    return (
      <div className="pb-16">
        <div className="flex items-center gap-4 border-b border-border pb-7 pt-10">
          <div className="h-11 w-11 animate-pulse rounded-xl bg-muted" />
          <div className="space-y-2">
            <div className="h-7 w-40 animate-pulse rounded bg-muted" />
            <div className="h-4 w-72 animate-pulse rounded bg-muted" />
          </div>
        </div>
        <div className="mt-8 grid grid-cols-1 gap-4 xl:grid-cols-2">
          {Array.from({ length: 4 }).map((_, i) => (
            <div key={i} className="h-40 animate-pulse rounded-xl bg-muted" />
          ))}
        </div>
      </div>
    );
  }

  return (
    <div className="pb-20">
      <PageHeader
        eyebrow="Sent"
        title="Weekly History"
        description="Every item the digest delivered this week, with the source link it was summarised from."
        icon={Clock}
        metric={{ value: entries.length, label: "Entries" }}
      />

      {entries.length === 0 ? (
        <div className="mt-8">
          <EmptyState
            icon={Inbox}
            title="Nothing sent this week yet"
            description="Items appear here after each daily digest run."
          />
        </div>
      ) : (
        <div className="mt-8 grid grid-cols-1 gap-4 xl:grid-cols-2">
          {entries.map((entry, i) => {
            const voted = votes[entry.url];
            return (
              <Card
                key={`${entry.date}-${i}`}
                interactive
                className="flex flex-col overflow-hidden"
              >
                <CardContent className="flex flex-1 flex-col p-5 sm:p-6">
                  {/* Meta row */}
                  <div className="flex flex-wrap items-center gap-2">
                    <span className="font-mono text-[0.6875rem] uppercase tracking-[0.08em] text-subtle-foreground">
                      {formatDate(entry.date)}
                    </span>
                    <span
                      className="h-1 w-1 rounded-full bg-border-strong"
                      aria-hidden="true"
                    />
                    <span className="text-xs font-medium text-foreground">
                      {entry.source || entry.authors}
                    </span>
                    {getTopicBadge(entry.topic_id)}
                    {entry.release_type && (
                      <Badge variant="outline" className="font-mono text-[0.6875rem]">
                        {entry.release_type}
                      </Badge>
                    )}

                    {/* Feedback buttons */}
                    <div className="ml-auto flex shrink-0 items-center gap-1">
                      <button
                        onClick={() => submitFeedback(entry, 1)}
                        disabled={!!voted}
                        aria-label="Thumbs up"
                        className={cn(
                          "flex h-7 w-7 items-center justify-center rounded-lg border transition-colors",
                          voted === 1
                            ? "border-success/30 bg-success/10 text-success"
                            : voted
                            ? "cursor-not-allowed border-transparent text-subtle-foreground/40"
                            : "border-transparent text-subtle-foreground hover:border-success/30 hover:bg-success/10 hover:text-success",
                        )}
                      >
                        <ThumbsUp className="h-3.5 w-3.5" />
                      </button>
                      <button
                        onClick={() => submitFeedback(entry, -1)}
                        disabled={!!voted}
                        aria-label="Thumbs down"
                        className={cn(
                          "flex h-7 w-7 items-center justify-center rounded-lg border transition-colors",
                          voted === -1
                            ? "border-destructive/30 bg-destructive/10 text-destructive"
                            : voted
                            ? "cursor-not-allowed border-transparent text-subtle-foreground/40"
                            : "border-transparent text-subtle-foreground hover:border-destructive/30 hover:bg-destructive/10 hover:text-destructive",
                        )}
                      >
                        <ThumbsDown className="h-3.5 w-3.5" />
                      </button>
                    </div>
                  </div>

                  {/* Headline */}
                  <h2 className="mt-3 font-display text-lg font-semibold leading-snug text-foreground">
                    {entry.title}
                  </h2>

                  {entry.what_shipped && (
                    <p className="mt-2.5 text-sm leading-relaxed text-muted-foreground">
                      {entry.what_shipped}
                    </p>
                  )}

                  {entry.why_it_matters && (
                    <p className="mt-4 border-l-2 border-primary/30 pl-3.5 text-sm leading-relaxed text-foreground/80">
                      {entry.why_it_matters}
                    </p>
                  )}

                  {entry.url && (
                    <a
                      href={entry.url}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="mt-auto inline-flex self-start items-center gap-1.5 pt-5 text-xs font-medium text-primary transition-colors hover:text-primary/80"
                    >
                      View source
                      <ExternalLink className="h-3.5 w-3.5" />
                    </a>
                  )}
                </CardContent>
              </Card>
            );
          })}
        </div>
      )}
    </div>
  );
}
