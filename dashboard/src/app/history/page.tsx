"use client";

import { useState, useEffect, useCallback } from "react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { TOPICS, CATEGORY_BADGE_COLORS } from "@/lib/topics";
import { Clock, ExternalLink, Inbox, ThumbsUp, ThumbsDown } from "lucide-react";
import { format, parseISO } from "date-fns";

interface HistoryEntry {
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

function getTopicBadge(topicId?: string) {
  if (!topicId) return null;
  const topic = TOPICS.find((t) => t.id === topicId);
  if (!topic) return null;
  return (
    <Badge className={`text-xs font-mono ${CATEGORY_BADGE_COLORS[topic.category] || ""}`}>
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
      <div className="py-8">
        <div className="h-8 w-48 bg-muted rounded animate-pulse mb-8" />
        {Array.from({ length: 3 }).map((_, i) => (
          <div key={i} className="h-32 bg-muted rounded-lg animate-pulse mb-4" />
        ))}
      </div>
    );
  }

  return (
    <div className="py-8">
      <div className="mb-8">
        <div className="flex items-baseline gap-3 mb-1">
          <Clock className="h-7 w-7 text-primary shrink-0 self-center" />
          <h1 className="text-2xl font-display font-bold text-foreground">
            Weekly History
          </h1>
        </div>
        <p className="text-muted-foreground mt-1">
          Papers sent this week.{" "}
          <span className="font-mono text-sm text-muted-foreground/70">{entries.length} entries</span>
        </p>
      </div>

      {entries.length === 0 ? (
        <Card>
          <CardContent className="flex flex-col items-center justify-center py-16 text-center">
            <Inbox className="h-12 w-12 text-muted-foreground/40 mb-4" />
            <p className="text-muted-foreground font-medium">No papers sent this week yet</p>
            <p className="text-sm text-muted-foreground/70 mt-1">
              Papers will appear here after each daily digest run.
            </p>
          </CardContent>
        </Card>
      ) : (
        <div className="space-y-4">
          {entries.map((entry, i) => {
            const voted = votes[entry.url];
            return (
              <Card key={`${entry.date}-${i}`}>
                <CardHeader className="pb-3">
                  <div className="flex items-start justify-between gap-3">
                    <div className="space-y-1.5">
                      <p className="text-xs font-mono text-muted-foreground/70">
                        {formatDate(entry.date)}
                      </p>
                      {getTopicBadge(entry.topic_id)}
                    </div>
                    {/* Feedback buttons */}
                    <div className="flex items-center gap-1 shrink-0">
                      <button
                        onClick={() => submitFeedback(entry, 1)}
                        disabled={!!voted}
                        aria-label="Thumbs up"
                        className={`p-1.5 rounded-md transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring ${
                          voted === 1
                            ? "bg-green-100 text-green-700 dark:bg-green-900/40 dark:text-green-400"
                            : voted
                            ? "text-muted-foreground/30 cursor-not-allowed"
                            : "text-muted-foreground hover:text-green-600 hover:bg-green-50 dark:hover:text-green-400 dark:hover:bg-green-900/20"
                        }`}
                      >
                        <ThumbsUp className="h-4 w-4" />
                      </button>
                      <button
                        onClick={() => submitFeedback(entry, -1)}
                        disabled={!!voted}
                        aria-label="Thumbs down"
                        className={`p-1.5 rounded-md transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring ${
                          voted === -1
                            ? "bg-red-100 text-red-700 dark:bg-red-900/40 dark:text-red-400"
                            : voted
                            ? "text-muted-foreground/30 cursor-not-allowed"
                            : "text-muted-foreground hover:text-red-600 hover:bg-red-50 dark:hover:text-red-400 dark:hover:bg-red-900/20"
                        }`}
                      >
                        <ThumbsDown className="h-4 w-4" />
                      </button>
                    </div>
                  </div>
                  <CardTitle className="text-base mt-2">{entry.title}</CardTitle>
                  <p className="text-sm text-muted-foreground">
                    {entry.authors}
                    {entry.institution && ` — ${entry.institution}`}
                  </p>
                </CardHeader>
                <CardContent>
                  {entry.claim && (
                    <p className="text-sm text-foreground mb-2">
                      {entry.claim}
                    </p>
                  )}
                  {entry.safety_relevance && (
                    <p className="text-sm text-muted-foreground italic mb-3">
                      {entry.safety_relevance}
                    </p>
                  )}
                  {entry.rigor && (
                    <p className="text-xs font-mono text-muted-foreground/70 mb-3">
                      {entry.rigor}
                    </p>
                  )}
                  {entry.url && (
                    <a
                      href={entry.url}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="inline-flex items-center gap-1 text-sm text-primary hover:underline font-mono"
                    >
                      <ExternalLink className="h-3.5 w-3.5" />
                      View source
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
