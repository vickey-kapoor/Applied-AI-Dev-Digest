"use client";

import { useState, useEffect } from "react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { BarChart3, Trophy } from "lucide-react";

interface TopicStat {
  id: string;
  name: string;
  category: "core" | "applied" | "emerging";
  wins: number;
  pct: number;
}

const CATEGORY_COLORS: Record<string, string> = {
  core: "bg-blue-500",
  applied: "bg-purple-500",
  emerging: "bg-amber-500",
};

const CATEGORY_TAG_COLORS: Record<string, string> = {
  core: "text-blue-600 dark:text-blue-400",
  applied: "text-purple-600 dark:text-purple-400",
  emerging: "text-amber-600 dark:text-amber-400",
};

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

  if (loading) {
    return (
      <div className="p-8 max-w-3xl mx-auto">
        <div className="h-8 w-48 bg-gray-200 dark:bg-gray-800 rounded animate-pulse mb-8" />
        {Array.from({ length: 5 }).map((_, i) => (
          <div key={i} className="h-12 bg-gray-100 dark:bg-gray-800 rounded animate-pulse mb-3" />
        ))}
      </div>
    );
  }

  return (
    <div className="p-8 max-w-3xl mx-auto">
      <div className="mb-8">
        <div className="flex items-center gap-3 mb-1">
          <BarChart3 className="h-7 w-7 text-blue-600" />
          <h1 className="text-2xl font-display font-bold text-gray-900 dark:text-gray-100">
            Topic Performance
          </h1>
        </div>
        <p className="text-gray-500 mt-1">
          Which topics win the daily ranking most often.{" "}
          <span className="font-mono text-sm text-gray-400">{total} total digests</span>
        </p>
      </div>

      {total === 0 ? (
        <Card>
          <CardContent className="flex flex-col items-center justify-center py-16 text-center">
            <Trophy className="h-12 w-12 text-gray-300 dark:text-gray-600 mb-4" />
            <p className="text-gray-500 font-medium">No stats yet</p>
            <p className="text-sm text-gray-400 mt-1">
              Stats will accumulate as daily digests run.
            </p>
          </CardContent>
        </Card>
      ) : (
        <Card>
          <CardHeader>
            <CardTitle className="text-base">Win Distribution</CardTitle>
          </CardHeader>
          <CardContent className="space-y-4">
            {stats.map((stat) => (
              <div key={stat.id} className="space-y-1.5">
                <div className="flex items-center justify-between text-sm">
                  <div className="flex items-center gap-2">
                    <span className="font-medium text-gray-900 dark:text-gray-100">
                      {stat.name}
                    </span>
                    <span className={`text-xs font-mono ${CATEGORY_TAG_COLORS[stat.category]}`}>
                      {stat.category}
                    </span>
                  </div>
                  <span className="font-mono text-sm text-gray-500">
                    {stat.wins} <span className="text-gray-400">({stat.pct}%)</span>
                  </span>
                </div>
                <div className="h-3 w-full bg-gray-100 dark:bg-gray-800 rounded-full overflow-hidden">
                  <div
                    className={`h-full rounded-full transition-all ${CATEGORY_COLORS[stat.category]}`}
                    style={{ width: `${Math.max((stat.wins / maxWins) * 100, stat.wins > 0 ? 4 : 0)}%` }}
                  />
                </div>
              </div>
            ))}
          </CardContent>
        </Card>
      )}
    </div>
  );
}
