import { describe, expect, it } from "vitest";

import {
  CATEGORY_BADGE_COLORS,
  CATEGORY_BAR_COLORS,
  CATEGORY_TAG_COLORS,
  TOPICS,
  getActiveKeywords,
  getCategoryLabel,
  getDefaultTopicConfig,
} from "@/lib/topics";

/**
 * topics.ts is the dashboard half of a mirror: src/topic_config.py holds the
 * same ids, names, keywords and defaults on the Python side, and the digest
 * pipeline reads from that copy. Drift between the two is silent — the
 * dashboard would toggle topics the fetcher does not filter on — so these
 * tests pin the invariants that make the mirror checkable.
 */
describe("TOPICS", () => {
  it("defines eleven topics", () => {
    expect(TOPICS).toHaveLength(11);
  });

  it("has unique ids", () => {
    const ids = TOPICS.map((t) => t.id);
    expect(new Set(ids).size).toBe(ids.length);
  });

  it("enables the six core topics plus both applied ones by default", () => {
    // open_weights and infrastructure are "applied" and used to default off,
    // which left the digest blind to what the reader can actually run and to
    // the serving and inference economics they build against. Mirrors
    // DEFAULT_TOPICS in src/topic_config.py.
    const enabled = TOPICS.filter((t) => t.defaultEnabled).map((t) => t.id);
    expect(enabled.sort()).toEqual(
      [
        "agents_tooling",
        "benchmarks",
        "infrastructure",
        "lab_research",
        "model_releases",
        "open_weights",
        "product_api",
        "safety_system_cards",
      ].sort(),
    );
  });

  it("enables only core and applied topics by default, never emerging", () => {
    for (const topic of TOPICS.filter((t) => t.defaultEnabled)) {
      expect(["core", "applied"]).toContain(topic.category);
    }
  });

  it("gives every topic a name, description and at least one keyword", () => {
    for (const topic of TOPICS) {
      expect(topic.name.length).toBeGreaterThan(0);
      expect(topic.description.length).toBeGreaterThan(0);
      expect(topic.keywords.length).toBeGreaterThan(0);
    }
  });

  it("has no duplicate keywords within a topic", () => {
    for (const topic of TOPICS) {
      const lowered = topic.keywords.map((k) => k.toLowerCase());
      expect(new Set(lowered).size).toBe(lowered.length);
    }
  });

  it("uses only categories that have colours defined", () => {
    for (const topic of TOPICS) {
      expect(CATEGORY_BADGE_COLORS[topic.category]).toBeDefined();
      expect(CATEGORY_BAR_COLORS[topic.category]).toBeDefined();
      expect(CATEGORY_TAG_COLORS[topic.category]).toBeDefined();
      expect(getCategoryLabel(topic.category)).toBeTruthy();
    }
  });
});

describe("getDefaultTopicConfig", () => {
  it("returns an entry for every topic", () => {
    const config = getDefaultTopicConfig();
    expect(Object.keys(config).sort()).toEqual(TOPICS.map((t) => t.id).sort());
  });

  it("mirrors each topic's defaultEnabled flag", () => {
    const config = getDefaultTopicConfig();
    for (const topic of TOPICS) {
      expect(config[topic.id]).toBe(topic.defaultEnabled);
    }
  });
});

describe("getActiveKeywords", () => {
  it("returns nothing when every topic is off", () => {
    const config = Object.fromEntries(TOPICS.map((t) => [t.id, false]));
    expect(getActiveKeywords(config)).toEqual([]);
  });

  it("returns only the enabled topic's keywords", () => {
    const config = Object.fromEntries(
      TOPICS.map((t) => [t.id, t.id === "model_releases"]),
    );
    const keywords = getActiveKeywords(config);
    const expected = TOPICS.find((t) => t.id === "model_releases")!.keywords;

    expect(keywords.sort()).toEqual([...expected].sort());
  });

  it("deduplicates keywords shared between enabled topics", () => {
    const config = Object.fromEntries(TOPICS.map((t) => [t.id, true]));
    const keywords = getActiveKeywords(config);

    expect(new Set(keywords).size).toBe(keywords.length);
  });

  it("returns keywords sorted, so callers get a stable order", () => {
    const keywords = getActiveKeywords(getDefaultTopicConfig());
    expect(keywords).toEqual([...keywords].sort());
  });

  it("treats a missing topic id as disabled rather than throwing", () => {
    expect(() => getActiveKeywords({})).not.toThrow();
    expect(getActiveKeywords({})).toEqual([]);
  });
});
