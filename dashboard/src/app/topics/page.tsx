"use client";

import { useState, useEffect, useCallback } from "react";
import { TOPICS, getCategoryLabel, getDefaultTopicConfig, type TopicConfig, type Topic } from "@/lib/topics";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Layers, Save, Loader2, Check, AlertCircle, Plus, X, ChevronDown } from "lucide-react";

type SaveStatus = "idle" | "saving" | "saved" | "error";
type CustomKeywordsMap = Record<string, string[]>;

const CATEGORY_ORDER: Topic["category"][] = ["core", "applied", "emerging"];

const CATEGORY_DESCRIPTIONS: Record<Topic["category"], string> = {
  core: "Always-on topics that form the backbone of your digest",
  applied: "Domain-specific topics you can toggle by interest",
  emerging: "Cutting-edge areas worth keeping an eye on",
};

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
      <div className="py-8">
        <div className="mb-8">
          <div className="h-8 w-48 bg-muted rounded animate-pulse" />
          <div className="h-4 w-96 bg-muted rounded animate-pulse mt-2" />
        </div>
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          {Array.from({ length: 6 }).map((_, i) => (
            <div key={i} className="h-48 bg-muted rounded-lg animate-pulse" />
          ))}
        </div>
      </div>
    );
  }

  return (
    <div className="py-8 pb-28">
      {/* Header */}
      <div className="mb-8">
        <div className="flex items-baseline gap-3 mb-1">
          <Layers className="h-7 w-7 text-primary shrink-0 self-center" />
          <h1 className="text-2xl font-display font-bold text-foreground">
            Topics
          </h1>
        </div>
        <p className="text-muted-foreground mt-1">
          Choose which AI research topics appear in your daily digest.{" "}
          <span className="font-mono text-sm text-muted-foreground/70">
            {enabledCount} of {TOPICS.length} active
          </span>
        </p>
      </div>

      {/* Topic sections */}
      {CATEGORY_ORDER.map((category) => {
        const topics = TOPICS.filter((t) => t.category === category);
        return (
          <section key={category} className="mb-10">
            <div className="mb-4">
              <h2 className="text-lg font-display font-semibold text-foreground">
                {getCategoryLabel(category)}
              </h2>
              <p className="text-sm text-muted-foreground/70">{CATEGORY_DESCRIPTIONS[category]}</p>
            </div>
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
              {topics.map((topic) => {
                const enabled = config?.[topic.id] ?? topic.defaultEnabled;
                const isExpanded = expandedTopics.has(topic.id);
                const topicCustom = customKeywords[topic.id] || [];

                return (
                  <Card
                    key={topic.id}
                    className={`transition-all ${
                      enabled
                        ? "ring-2 ring-primary/30"
                        : "opacity-60 hover:opacity-80"
                    }`}
                  >
                    <CardHeader className="pb-3">
                      <div className="flex items-start justify-between">
                        <CardTitle
                          className="text-base cursor-pointer"
                          onClick={() => toggle(topic.id)}
                        >
                          {topic.name}
                        </CardTitle>
                        <button
                          role="switch"
                          aria-checked={enabled}
                          aria-label={`Toggle ${topic.name}`}
                          onClick={() => toggle(topic.id)}
                          className={`relative inline-flex h-6 w-11 items-center rounded-full transition-colors shrink-0 ${
                            enabled ? "bg-primary" : "bg-muted-foreground/30"
                          }`}
                        >
                          <span
                            className={`inline-block h-4 w-4 rounded-full bg-white dark:bg-foreground transition-transform ${
                              enabled ? "translate-x-6" : "translate-x-1"
                            }`}
                          />
                        </button>
                      </div>
                      <p className="text-sm text-muted-foreground mt-1">
                        {topic.description}
                      </p>
                    </CardHeader>
                    <CardContent>
                      {/* Default keywords */}
                      <div className="flex flex-wrap gap-1.5">
                        {topic.keywords.map((kw) => (
                          <Badge key={kw} variant="secondary" className="text-xs font-mono">
                            {kw}
                          </Badge>
                        ))}
                        {/* Custom keywords */}
                        {topicCustom.map((kw) => (
                          <Badge
                            key={`custom-${kw}`}
                            className="text-xs font-mono bg-emerald-100 text-emerald-800 dark:bg-emerald-900/40 dark:text-emerald-300 gap-1 cursor-pointer hover:bg-emerald-200 dark:hover:bg-emerald-900/60"
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
                        className="mt-3 flex items-center gap-1 text-xs text-muted-foreground hover:text-foreground transition-colors"
                      >
                        <ChevronDown className={`h-3.5 w-3.5 transition-transform ${isExpanded ? "rotate-180" : ""}`} />
                        {isExpanded ? "Hide" : "Add keywords"}
                      </button>

                      {/* Custom keyword input */}
                      {isExpanded && (
                        <div className="mt-2 flex gap-2">
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
                            className="flex-1 px-2.5 py-1.5 text-sm font-mono rounded-md border border-border bg-background text-foreground placeholder:text-muted-foreground focus:outline-none focus:ring-2 focus:ring-primary/40"
                          />
                          <button
                            onClick={() => addCustomKeyword(topic.id)}
                            className="p-1.5 rounded-md bg-emerald-600 dark:bg-emerald-500 text-white hover:bg-emerald-700 dark:hover:bg-emerald-600 transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
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
          </section>
        );
      })}

      {/* Sticky save bar */}
      <div className="fixed bottom-0 left-0 right-0 z-30 pb-[env(safe-area-inset-bottom)]">
        <div
          className={`border-t border-border bg-background/95 backdrop-blur px-8 py-4 flex items-center justify-between transition-opacity ${
            isDirty || saveStatus !== "idle" ? "opacity-100" : "opacity-0 pointer-events-none"
          }`}
        >
          <div className="text-sm text-muted-foreground">
            {isDirty && "You have unsaved changes"}
            {saveStatus === "saved" && (
              <span className="flex items-center gap-1 text-green-600 dark:text-green-400">
                <Check className="h-4 w-4" /> Changes saved
              </span>
            )}
            {saveStatus === "error" && (
              <span role="alert" className="flex items-center gap-1 text-red-600 dark:text-red-400">
                <AlertCircle className="h-4 w-4" /> Failed to save — is Vercel KV configured?
              </span>
            )}
          </div>
          <button
            onClick={save}
            disabled={!isDirty || saveStatus === "saving"}
            className="inline-flex items-center gap-2 px-5 py-2 bg-primary text-white text-sm font-medium rounded-lg hover:bg-primary/80 disabled:opacity-50 disabled:cursor-not-allowed transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
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
