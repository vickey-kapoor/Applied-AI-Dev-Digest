"use client";

import { useState, useEffect, useCallback } from "react";
import {
  TOPICS,
  CATEGORY_DOT_COLORS,
  getCategoryLabel,
  getDefaultTopicConfig,
  type TopicConfig,
  type Topic,
} from "@/lib/topics";
import { Card, CardContent, CardHeader } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { PageHeader } from "@/components/ui/page-header";
import { buttonVariants } from "@/components/ui/button";
import { cn } from "@/lib/utils";
import {
  Layers,
  Save,
  Loader2,
  Check,
  AlertCircle,
  Plus,
  X,
  ChevronDown,
} from "lucide-react";

type SaveStatus = "idle" | "saving" | "saved" | "error";
type CustomKeywordsMap = Record<string, string[]>;

const CATEGORY_ORDER: Topic["category"][] = ["core", "applied"];

const CATEGORY_DESCRIPTIONS: Record<Topic["category"], string> = {
  core: "Always-on topics that form the backbone of your digest",
  applied: "Domain-specific topics you can toggle by interest",
};

/** Every topic, grouped by category, flattened into one render order. */
const ORDERED_TOPICS = CATEGORY_ORDER.flatMap((category) =>
  TOPICS.filter((t) => t.category === category),
);

/** Keywords shown before the list collapses behind a "+N" chip. */
const KEYWORD_PREVIEW_COUNT = 6;

export default function TopicsPage() {
  const [config, setConfig] = useState<TopicConfig | null>(null);
  const [savedConfig, setSavedConfig] = useState<TopicConfig | null>(null);
  const [customKeywords, setCustomKeywords] = useState<CustomKeywordsMap>({});
  const [savedCustomKeywords, setSavedCustomKeywords] = useState<CustomKeywordsMap>({});
  const [loading, setLoading] = useState(true);
  const [saveStatus, setSaveStatus] = useState<SaveStatus>("idle");
  const [expandedTopics, setExpandedTopics] = useState<Set<string>>(new Set());
  const [newKeywordInputs, setNewKeywordInputs] = useState<Record<string, string>>({});

  useEffect(() => {
    fetch("/api/topics")
      .then((res) => res.json())
      .then((data: { config: TopicConfig; customKeywords: CustomKeywordsMap }) => {
        setConfig(data.config);
        setSavedConfig(data.config);
        setCustomKeywords(data.customKeywords || {});
        setSavedCustomKeywords(data.customKeywords || {});
      })
      .catch(() => {
        const defaults = getDefaultTopicConfig();
        setConfig(defaults);
        setSavedConfig(defaults);
      })
      .finally(() => setLoading(false));
  }, []);

  const isDirty =
    (config !== null && savedConfig !== null && JSON.stringify(config) !== JSON.stringify(savedConfig)) ||
    JSON.stringify(customKeywords) !== JSON.stringify(savedCustomKeywords);

  const toggle = useCallback((id: string) => {
    setConfig((prev) => (prev ? { ...prev, [id]: !prev[id] } : prev));
    setSaveStatus("idle");
  }, []);

  const toggleExpand = useCallback((id: string) => {
    setExpandedTopics((prev) => {
      const next = new Set(prev);
      if (next.has(id)) next.delete(id);
      else next.add(id);
      return next;
    });
  }, []);

  const addCustomKeyword = useCallback((topicId: string) => {
    const keyword = (newKeywordInputs[topicId] || "").trim().toLowerCase();
    if (!keyword) return;
    setCustomKeywords((prev) => {
      const existing = prev[topicId] || [];
      if (existing.includes(keyword)) return prev;
      return { ...prev, [topicId]: [...existing, keyword] };
    });
    setNewKeywordInputs((prev) => ({ ...prev, [topicId]: "" }));
    setSaveStatus("idle");
  }, [newKeywordInputs]);

  const removeCustomKeyword = useCallback((topicId: string, keyword: string) => {
    setCustomKeywords((prev) => {
      const existing = (prev[topicId] || []).filter((k) => k !== keyword);
      if (existing.length === 0) {
        // eslint-disable-next-line @typescript-eslint/no-unused-vars
      const { [topicId]: _, ...rest } = prev;
        return rest;
      }
      return { ...prev, [topicId]: existing };
    });
    setSaveStatus("idle");
  }, []);

  const save = useCallback(async () => {
    if (!config) return;
    setSaveStatus("saving");
    try {
      const res = await fetch("/api/topics", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ config, customKeywords }),
      });
      if (!res.ok) throw new Error(await res.text());
      setSavedConfig({ ...config });
      setSavedCustomKeywords({ ...customKeywords });
      setSaveStatus("saved");
      setTimeout(() => setSaveStatus("idle"), 2000);
    } catch {
      setSaveStatus("error");
    }
  }, [config, customKeywords]);

  const enabledCount = config ? Object.values(config).filter(Boolean).length : 0;

  if (loading) {
    return (
      <div className="pb-16">
        <div className="flex items-center gap-4 border-b border-border pb-7 pt-10">
          <div className="h-11 w-11 animate-pulse rounded-xl bg-muted" />
          <div className="space-y-2">
            <div className="h-7 w-40 animate-pulse rounded bg-muted" />
            <div className="h-4 w-80 animate-pulse rounded bg-muted" />
          </div>
        </div>
        <div className="mt-6 grid grid-cols-1 gap-3.5 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4">
          {Array.from({ length: 8 }).map((_, i) => (
            <div key={i} className="h-52 animate-pulse rounded-xl bg-muted" />
          ))}
        </div>
      </div>
    );
  }

  return (
    <div className="pb-28">
      <PageHeader
        eyebrow="Configuration"
        title="Topics"
        description="Choose which AI research topics appear in your daily digest. Keywords are what the fetcher filters on."
        icon={Layers}
        metric={{
          value: (
            <>
              {enabledCount}
              <span className="text-subtle-foreground">/{TOPICS.length}</span>
            </>
          ),
          label: "Active",
        }}
      />

      {/* Category legend — the grouping the three sections used to carry */}
      <div className="mt-6 grid grid-cols-1 gap-x-8 gap-y-3 rounded-xl border border-border bg-surface px-5 py-4 sm:grid-cols-3">
        {CATEGORY_ORDER.map((category) => {
          const inCategory = TOPICS.filter((t) => t.category === category);
          const activeInCategory = inCategory.filter(
            (t) => config?.[t.id] ?? t.defaultEnabled,
          ).length;
          return (
            <div key={category} className="flex items-baseline gap-2.5">
              <span
                className={cn(
                  "h-2 w-2 shrink-0 translate-y-px rounded-full",
                  CATEGORY_DOT_COLORS[category],
                )}
                aria-hidden="true"
              />
              <div className="min-w-0">
                <p className="text-sm font-semibold text-foreground">
                  {getCategoryLabel(category)}
                  <span className="ml-2 font-mono text-xs font-normal text-subtle-foreground">
                    {activeInCategory}/{inCategory.length} on
                  </span>
                </p>
                <p className="mt-0.5 text-[0.8125rem] leading-snug text-muted-foreground">
                  {CATEGORY_DESCRIPTIONS[category]}
                </p>
              </div>
            </div>
          );
        })}
      </div>

      {/* One grid for every topic — grouped by category, but without the
          ragged half-empty rows three separate grids produced. */}
      <div className="mt-5 grid grid-cols-1 gap-3.5 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4">
        {ORDERED_TOPICS.map((topic) => {
          const enabled = config?.[topic.id] ?? topic.defaultEnabled;
          const isExpanded = expandedTopics.has(topic.id);
          const topicCustom = customKeywords[topic.id] || [];
          const visibleKeywords = isExpanded
            ? topic.keywords
            : topic.keywords.slice(0, KEYWORD_PREVIEW_COUNT);
          const hiddenCount = topic.keywords.length - visibleKeywords.length;

          return (
            <Card
              key={topic.id}
              elevation={enabled ? "low" : "flat"}
              className={cn(
                "flex flex-col transition-[border-color,background-color,opacity,box-shadow] duration-200",
                enabled
                  ? "border-primary/25"
                  : "bg-surface opacity-75 hover:opacity-100",
              )}
            >
              <CardHeader className="gap-0 space-y-0 p-4 pb-3">
                <div className="flex items-center justify-between gap-3">
                  <span className="flex min-w-0 items-center gap-2">
                    <span
                      className={cn(
                        "h-1.5 w-1.5 shrink-0 rounded-full",
                        CATEGORY_DOT_COLORS[topic.category],
                      )}
                      aria-hidden="true"
                    />
                    <span className="font-mono text-[0.625rem] uppercase tracking-[0.1em] text-subtle-foreground">
                      {getCategoryLabel(topic.category)}
                    </span>
                  </span>
                  <button
                    role="switch"
                    aria-checked={enabled}
                    aria-label={`Toggle ${topic.name}`}
                    onClick={() => toggle(topic.id)}
                    className={cn(
                      "relative inline-flex h-5 w-9 shrink-0 items-center rounded-full border transition-colors",
                      enabled
                        ? "border-primary bg-primary"
                        : "border-border-strong bg-secondary",
                    )}
                  >
                    <span
                      className={cn(
                        "inline-block h-3.5 w-3.5 rounded-full shadow-e1 transition-transform",
                        enabled
                          ? "translate-x-[1.1rem] bg-white"
                          : "translate-x-[0.1875rem] bg-subtle-foreground",
                      )}
                    />
                  </button>
                </div>
                <h3
                  className="mt-2.5 cursor-pointer text-[0.9375rem] font-semibold leading-snug tracking-tight text-foreground"
                  onClick={() => toggle(topic.id)}
                >
                  {topic.name}
                </h3>
                <p className="mt-1.5 min-h-[3.1rem] text-[0.8125rem] leading-snug text-muted-foreground">
                  {topic.description}
                </p>
              </CardHeader>

              <CardContent className="flex flex-1 flex-col p-4 pt-0">
                {/* Keywords */}
                <div className="flex flex-wrap gap-1">
                  {visibleKeywords.map((kw) => (
                    <Badge
                      key={kw}
                      variant="secondary"
                      className="font-mono text-[0.6875rem]"
                    >
                      {kw}
                    </Badge>
                  ))}
                  {hiddenCount > 0 && (
                    <button
                      onClick={() => toggleExpand(topic.id)}
                      className="rounded-md border border-dashed border-border-strong px-2 py-0.5 font-mono text-[0.6875rem] leading-5 text-subtle-foreground transition-colors hover:border-primary/40 hover:text-foreground"
                    >
                      +{hiddenCount}
                    </button>
                  )}
                  {/* Custom keywords */}
                  {topicCustom.map((kw) => (
                    <Badge
                      key={`custom-${kw}`}
                      variant="accent"
                      className="cursor-pointer font-mono text-[0.6875rem]"
                      onClick={() => removeCustomKeyword(topic.id, kw)}
                    >
                      {kw}
                      <X className="h-3 w-3" />
                    </Badge>
                  ))}
                </div>

                {/* Expand toggle */}
                <button
                  onClick={() => toggleExpand(topic.id)}
                  className="mt-auto flex items-center gap-1.5 pt-3 text-xs font-medium text-subtle-foreground transition-colors hover:text-foreground"
                >
                  <ChevronDown
                    className={cn(
                      "h-3.5 w-3.5 transition-transform",
                      isExpanded && "rotate-180",
                    )}
                  />
                  {isExpanded ? "Hide keywords" : "Add keywords"}
                </button>

                {/* Custom keyword input */}
                {isExpanded && (
                  <div className="mt-3 flex gap-2">
                    <input
                      type="text"
                      placeholder="Add keyword..."
                      value={newKeywordInputs[topic.id] || ""}
                      onChange={(e) =>
                        setNewKeywordInputs((prev) => ({
                          ...prev,
                          [topic.id]: e.target.value,
                        }))
                      }
                      onKeyDown={(e) => {
                        if (e.key === "Enter") addCustomKeyword(topic.id);
                      }}
                      className="h-8 min-w-0 flex-1 rounded-lg border border-input bg-background px-2.5 font-mono text-xs text-foreground transition-colors placeholder:text-subtle-foreground hover:border-border-strong"
                    />
                    <button
                      onClick={() => addCustomKeyword(topic.id)}
                      aria-label={`Add keyword to ${topic.name}`}
                      className={cn(
                        buttonVariants({ variant: "primary", size: "icon" }),
                      )}
                    >
                      <Plus className="h-4 w-4" />
                    </button>
                  </div>
                )}
              </CardContent>
            </Card>
          );
        })}
      </div>

      {/* Sticky save bar */}
      <div className="pointer-events-none fixed inset-x-0 bottom-0 z-30 px-5 pb-[max(1rem,env(safe-area-inset-bottom))] sm:px-8 lg:left-60 lg:px-10 xl:px-14">
        <div
          className={cn(
            "surface-highlight flex w-full items-center justify-between gap-4 rounded-xl border border-border bg-card/95 px-4 py-3 shadow-e3 backdrop-blur-xl transition-all duration-200",
            isDirty || saveStatus !== "idle"
              ? "pointer-events-auto translate-y-0 opacity-100"
              : "translate-y-3 opacity-0",
          )}
        >
          <div className="min-w-0 text-sm">
            {isDirty && saveStatus === "idle" && (
              <span className="flex items-center gap-2 text-muted-foreground">
                <span className="h-1.5 w-1.5 shrink-0 rounded-full bg-warning" />
                You have unsaved changes
              </span>
            )}
            {saveStatus === "saving" && (
              <span className="text-muted-foreground">Saving…</span>
            )}
            {saveStatus === "saved" && (
              <span className="flex items-center gap-2 text-success">
                <Check className="h-4 w-4 shrink-0" /> Changes saved
              </span>
            )}
            {saveStatus === "error" && (
              <span
                role="alert"
                className="flex items-center gap-2 text-destructive"
              >
                <AlertCircle className="h-4 w-4 shrink-0" />
                <span className="truncate">
                  Failed to save — is Vercel KV configured?
                </span>
              </span>
            )}
          </div>
          <button
            onClick={save}
            disabled={!isDirty || saveStatus === "saving"}
            className={cn(buttonVariants({ variant: "primary", size: "md" }))}
          >
            {saveStatus === "saving" ? (
              <Loader2 className="h-4 w-4 animate-spin" />
            ) : (
              <Save className="h-4 w-4" />
            )}
            Save changes
          </button>
        </div>
      </div>
    </div>
  );
}
