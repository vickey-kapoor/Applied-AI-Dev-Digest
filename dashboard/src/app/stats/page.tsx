"use client";

import { useState, useEffect } from "react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { PageHeader } from "@/components/ui/page-header";
import { EmptyState } from "@/components/ui/empty-state";
import { BarChart3, Trophy } from "lucide-react";
import {
  CATEGORY_BAR_COLORS,
  CATEGORY_DOT_COLORS,
  CATEGORY_TAG_COLORS,
  getCategoryLabel,
  type Topic,
} from "@/lib/topics";
import { cn } from "@/lib/utils";

interface TopicStat {
  id: string;
  name: string;
  category: "core" | "applied";
  wins: number;
  pct: number;
}

const CATEGORIES: Topic["category"][] = ["core", "applied"];

export default function StatsPage() {
  const [stats, setStats] = useState<TopicStat[]>([]);
  const [total, setTotal] = useState(0);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetch("/api/stats")
      .then((r) => r.json())
      .then((d) => {
        setStats(d.stats || []);
        setTotal(d.total || 0);
      })
      .catch(() => {})
      .finally(() => setLoading(false));
  }, []);

  const maxWins = Math.max(...stats.map((s) => s.wins), 1);
  const leader = stats.length > 0 ? stats[0] : null;
  const topicsSeen = stats.filter((s) => s.wins > 0).length;

  if (loading) {
    return (
      <div className="pb-16">
        <div className="flex items-center gap-4 border-b border-border pb-7 pt-10">
          <div className="h-11 w-11 animate-pulse rounded-xl bg-muted" />
          <div className="space-y-2">
            <div className="h-7 w-52 animate-pulse rounded bg-muted" />
            <div className="h-4 w-72 animate-pulse rounded bg-muted" />
          </div>
        </div>
        <div className="mt-10 space-y-3">
          {Array.from({ length: 6 }).map((_, i) => (
            <div key={i} className="h-14 animate-pulse rounded-xl bg-muted" />
          ))}
        </div>
      </div>
    );
  }

  return (
    <div className="pb-20">
      <PageHeader
        eyebrow="Analytics"
        title="Topic Performance"
        description="Which topics win the daily ranking most often, across every digest sent so far."
        icon={BarChart3}
        metric={{ value: total, label: "Digests" }}
      />

      {total === 0 ? (
        <div className="mt-8">
          <EmptyState
            icon={Trophy}
            title="No stats yet"
            description="Stats accumulate as daily digests run — check back after the next few sends."
          />
        </div>
      ) : (
        <>
          {/* Summary tiles */}
          <div className="mt-8 grid grid-cols-1 gap-4 sm:grid-cols-3">
            <Card className="p-5">
              <p className="eyebrow">Most frequent winner</p>
              <p className="mt-2 font-display text-xl font-semibold leading-tight text-foreground">
                {leader?.name ?? "—"}
              </p>
              <p className="mt-1 font-mono text-xs text-muted-foreground">
                {leader ? `${leader.wins} wins · ${leader.pct}%` : "—"}
              </p>
            </Card>
            <Card className="p-5">
              <p className="eyebrow">Topics that have won</p>
              <p className="mt-2 font-display text-xl font-semibold leading-tight text-foreground">
                {topicsSeen}
                <span className="text-subtle-foreground">/{stats.length}</span>
              </p>
              <p className="mt-1 font-mono text-xs text-muted-foreground">
                at least one digest
              </p>
            </Card>
            <Card className="p-5">
              <p className="eyebrow">Digests ranked</p>
              <p className="mt-2 font-display text-xl font-semibold leading-tight text-foreground">
                {total}
              </p>
              <p className="mt-1 font-mono text-xs text-muted-foreground">
                since tracking began
              </p>
            </Card>
          </div>

          <Card className="mt-6">
            <CardHeader className="flex-row items-center justify-between space-y-0 border-b border-border pb-4">
              <CardTitle>Win distribution</CardTitle>
              {/* Category legend */}
              <div className="flex items-center gap-4">
                {CATEGORIES.map((category) => (
                  <span
                    key={category}
                    className="flex items-center gap-1.5 text-xs text-muted-foreground"
                  >
                    <span
                      className={cn(
                        "h-2 w-2 rounded-full",
                        CATEGORY_DOT_COLORS[category],
                      )}
                      aria-hidden="true"
                    />
                    {getCategoryLabel(category)}
                  </span>
                ))}
              </div>
            </CardHeader>
            <CardContent className="divide-y divide-border p-0">
              {stats.map((stat, i) => (
                <div
                  key={stat.id}
                  className="flex items-center gap-4 px-5 py-3.5 transition-colors hover:bg-surface"
                >
                  <span className="w-5 shrink-0 font-mono text-xs tabular-nums text-subtle-foreground">
                    {String(i + 1).padStart(2, "0")}
                  </span>

                  <div className="min-w-0 flex-1">
                    <div className="flex items-baseline justify-between gap-3">
                      <span className="truncate text-sm font-medium text-foreground">
                        {stat.name}
                      </span>
                      <span className="shrink-0 font-mono text-xs tabular-nums text-muted-foreground">
                        {stat.wins}
                        <span className="text-subtle-foreground">
                          {" "}
                          · {stat.pct}%
                        </span>
                      </span>
                    </div>
                    <div className="mt-2 h-1.5 w-full overflow-hidden rounded-full bg-secondary">
                      <div
                        className={cn(
                          "h-full rounded-full transition-[width] duration-500",
                          CATEGORY_BAR_COLORS[stat.category],
                        )}
                        style={{
                          width: `${Math.max(
                            (stat.wins / maxWins) * 100,
                            stat.wins > 0 ? 3 : 0,
                          )}%`,
                        }}
                      />
                    </div>
                  </div>

                  <span
                    className={cn(
                      "hidden w-20 shrink-0 text-right font-mono text-[0.6875rem] uppercase tracking-[0.08em] sm:block",
                      CATEGORY_TAG_COLORS[stat.category],
                    )}
                  >
                    {stat.category}
                  </span>
                </div>
              ))}
            </CardContent>
          </Card>
        </>
      )}
    </div>
  );
}
