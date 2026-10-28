import { describe, expect, it } from "vitest";

import {
  CATEGORY_BADGE_COLORS,
  CATEGORY_BAR_COLORS,
  CATEGORY_TAG_COLORS,
  RETIRED_TOPIC_IDS,
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
  it("defines nine topics", () => {
    // Eleven until the 28-Oct-2026 audit retired enterprise_deployment and
    // policy_regulation, neither of which had ever produced a digest.
    expect(TOPICS).toHaveLength(9);
  });

  it("lists the retired topic ids without defining them", () => {
    const ids = TOPICS.map((t) => t.id);
    for (const retired of RETIRED_TOPIC_IDS) {
      expect(ids).not.toContain(retired);
    }
  });

  it("has unique ids", () => {
    const ids = TOPICS.map((t) => t.id);
    expect(new Set(ids).size).toBe(ids.length);
  });

  it("enables every topic by default", () => {
    // A disabled topic is inert, not merely untagged: it contributes no
    // keywords to the filter, so while multimodal was off a video or speech
    // model launch was dropped outright from the open sources. The audit
    // turned it on and retired the two that earned nothing, which leaves
    // nothing off. Mirrors DEFAULT_TOPICS in src/topic_config.py.
    const enabled = TOPICS.filter((t) => t.defaultEnabled).map((t) => t.id);
    expect(enabled.sort()).toEqual(TOPICS.map((t) => t.id).sort());
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
      const lowered = [...topic.keywords, ...(topic.weakKeywords ?? [])].map(
        (k) => k.toLowerCase(),
      );
      expect(new Set(lowered).size).toBe(lowered.length);
    }
  });

  it("never lists the same keyword under two topics", () => {
    // "Gemma" was in both model_releases and open_weights, and first-match
    // tagging meant open_weights never once received it.
    const seen = new Map<string, string>();
    for (const topic of TOPICS) {
      for (const kw of [...topic.keywords, ...(topic.weakKeywords ?? [])]) {
        const key = kw.toLowerCase();
        expect(seen.get(key), `${kw} is also under ${seen.get(key)}`).toBe(
          undefined,
        );
        seen.set(key, topic.id);
      }
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
      TOPICS.map((t) => [t.id, t.id === "lab_research"]),
    );
    const keywords = getActiveKeywords(config);
    const expected = TOPICS.find((t) => t.id === "lab_research")!.keywords;

    expect(keywords.sort()).toEqual([...expected].sort());
  });

  it("includes weak keywords, which filter even though they barely tag", () => {
    const config = Object.fromEntries(
      TOPICS.map((t) => [t.id, t.id === "model_releases"]),
    );
    const topic = TOPICS.find((t) => t.id === "model_releases")!;
    const keywords = getActiveKeywords(config);

    expect(topic.weakKeywords).toContain("Claude");
    expect(keywords.sort()).toEqual(
      [...topic.keywords, ...topic.weakKeywords!].sort(),
    );
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
