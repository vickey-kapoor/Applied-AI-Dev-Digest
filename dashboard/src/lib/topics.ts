export interface Topic {
  id: string;
  name: string;
  description: string;
  category: "core" | "applied";
  keywords: string[];
  /**
   * Keywords that admit an item but barely tag it. Bare model-family names
   * ("Claude", "GPT-") are what get a Hacker News story past the filter at
   * all, and they were also deciding its topic: over the 60 days to
   * 27-Oct-2026, 98 of Model Releases' 116 matches came from a brand name
   * alone with no release language anywhere, so an agent-harness post or an
   * SDK bump read as a model release. Mirrors `weak_keywords` in
   * src/topic_config.py, which scores them at a tenth of a normal keyword.
   */
  weakKeywords?: string[];
  defaultEnabled: boolean;
}

// Persona: engineer/researcher tracking what the frontier AI labs ship.
// "core"    = primary daily reading (releases, product/API, research, agents,
//             benchmarks, system cards, generative media)
// "applied" = how the models get deployed and run
//
// The 28-Oct-2026 topics audit (source-audit/2026-10-28-topics-audit.md in the
// project files) measured every topic and keyword against the 500-item pool in
// data/papers.json and the 60 digests to 27-Oct-2026. It removed 36 keywords
// that had never matched anything in 15 months, retired two topics that had
// never produced a digest, turned Multimodal on, and dropped the "emerging"
// category with them. Every keyword below has matched at least one real item;
// the single documented exception is "Sora", a weak keyword.

export type TopicConfig = Record<string, boolean>;

export const TOPICS: Topic[] = [
  // Core
  {
    id: "model_releases",
    name: "Model Releases",
    description: "New frontier models and versions from OpenAI, Anthropic, Google DeepMind, Meta, Mistral, xAI and others",
    category: "core",
    keywords: [
      "new model", "frontier model", "reasoning model", "model family",
      "introducing gpt",
    ],
    // "Command R" is gone: no match in 500 items. "model release", "flagship
    // model" and "introducing claude" went the same way — labs write
    // "Introducing X", never "model release".
    weakKeywords: [
      "GPT-", "Claude", "Gemini", "Llama", "Mistral", "Qwen",
      "DeepSeek", "Grok", "Gemma",
    ],
    defaultEnabled: true,
  },
  {
    id: "product_api",
    name: "Product & API",
    description: "AI API surfaces: endpoints, context windows and lengths, model deprecations",
    category: "core",
    // Mirrors src/topic_config.py. Generic terms were removed there because
    // they matched any software release ("public beta" admitted an
    // OpenStreetMap app; "SDK" admitted every client-library bump). Five of
    // the seven that remained had never matched anything either; "deprecat"
    // replaces "model deprecation" so it catches deprecated/deprecating too.
    keywords: [
      "responses api", "context window", "context length", "deprecat",
    ],
    defaultEnabled: true,
  },
  {
    id: "lab_research",
    name: "Lab Research",
    description: "Technical reports and papers from lab research teams — scaling, pretraining, post-training, RL",
    category: "core",
    keywords: [
      "technical report", "scaling law", "pretraining", "post-training",
      "reinforcement learning", "RLHF", "distillation",
      "mixture-of-experts", "long-context", "synthetic data",
    ],
    defaultEnabled: true,
  },
  {
    id: "agents_tooling",
    name: "Agents & Tooling",
    description: "Agentic systems, tool use, computer use, MCP, agent skills, coding agents",
    category: "core",
    keywords: [
      "agentic", "AI agent", "tool use", "tool calling",
      "tool definition", "computer use", "model context protocol",
      "agent skills", "coding agent", "browser agent", "multi-agent",
      "agent framework",
    ],
    defaultEnabled: true,
  },
  {
    id: "benchmarks",
    name: "Benchmarks & Evals",
    description: "Capability results and eval suites — SWE-bench, ARC-AGI, AIME, leaderboards",
    category: "core",
    keywords: [
      "benchmark", "leaderboard", "SWE-bench", "ARC-AGI", "AIME",
      "model evaluation",
    ],
    defaultEnabled: true,
  },
  {
    id: "safety_system_cards",
    name: "Safety & System Cards",
    description: "System cards and safety cases, misalignment and reward hacking, red-teaming, interpretability",
    category: "core",
    // Re-pointed at the vocabulary the labs publish under. "model card",
    // "responsible scaling", "frontier safety" and "safety evaluation" never
    // caught a lab safety post in 15 months; "jailbreak" caught a Nintendo
    // Switch jailbreak off Hacker News.
    keywords: [
      "system card", "safety case", "misalignment", "reward hacking",
      "eval awareness", "preparedness framework", "red-teaming",
      "red teaming", "prompt injection", "alignment",
      "interpretability",
    ],
    defaultEnabled: true,
  },
  {
    id: "multimodal",
    name: "Multimodal & Generative Media",
    description: "Vision, image, video, speech and world models shipped by the labs",
    category: "core",
    // On as of the audit. While it was off it contributed no keywords to the
    // filter at all, so a video or speech model launch was dropped outright
    // from Hacker News and HF Papers, and arrived from a lab's own blog with
    // no topic — DeepMind's "Genie 4" sat in the pool untagged.
    keywords: [
      "multimodal", "vision-language", "image generation",
      "video generation", "video model", "text-to-speech",
      "speech-to-text", "diffusion model", "world model",
      "world simulation",
    ],
    // Generative-media model families with no other route past the filter.
    // "Sora" has no match in the pool yet and is the one deliberate exception
    // to the measured-keywords rule; both are weak, so neither can decide a
    // topic on its own.
    weakKeywords: ["Sora", "Genie"],
    defaultEnabled: true,
  },
  // Applied
  {
    id: "open_weights",
    name: "Open Weights",
    description: "Open-weight model drops — Llama, Mistral, Qwen, DeepSeek, Gemma, OLMo",
    category: "applied",
    // "Gemma" lived here and in Model Releases, and first-match tagging meant
    // this topic never once received it. It is a Model Releases brand name
    // now; an open-weights Gemma post reaches this topic on "open-weight",
    // which outscores any brand name. "open weights" (spaced), "weights
    // release", "Apache 2.0" and "model license" never matched anything.
    keywords: [
      "open-weight", "open model", "open source model",
      "Hugging Face release", "OLMo",
    ],
    defaultEnabled: true,
  },
  {
    id: "infrastructure",
    name: "Compute & Infrastructure",
    description: "Training and serving infrastructure — accelerators, clusters, inference stacks, quantization",
    category: "applied",
    // "serving" is gone: 3 of its 4 matches were the word *preserving*.
    // "quantiz" replaces "quantization", which never matched on its own.
    keywords: [
      "inference", "quantiz", "gpu cluster", "TPU", "Blackwell",
      "Trainium", "supercomputer", "kv cache",
    ],
    defaultEnabled: true,
  },
];

// Retired by the audit, recorded here so a stats row or KV entry naming one is
// recognisable rather than mysterious. Mirrors RETIRED_TOPIC_IDS in
// src/topic_config.py.
//   enterprise_deployment — 4 matches in 60 days, three of them NVIDIA
//     consumer posts caught by "deployment", and never once the daily pick.
//   policy_regulation — 0 matches in 60 days, 8 of 9 keywords dead in 15
//     months. Regulation reaches this reader through the labs' own posts,
//     which are not keyword-filtered.
export const RETIRED_TOPIC_IDS = ["enterprise_deployment", "policy_regulation"];

/** Badge colors for category labels (used in history + stats pages) */
export const CATEGORY_BADGE_COLORS: Record<Topic["category"], string> = {
  core: "border-indigo-500/25 bg-indigo-500/10 text-indigo-700",
  applied: "border-teal-500/25 bg-teal-500/10 text-teal-700",
};

/** Progress bar fill colors (used in stats page) */
export const CATEGORY_BAR_COLORS: Record<Topic["category"], string> = {
  core: "bg-indigo-500",
  applied: "bg-teal-500",
};

/** Inline text colors for category tags (used in stats page) */
export const CATEGORY_TAG_COLORS: Record<Topic["category"], string> = {
  core: "text-indigo-600",
  applied: "text-teal-600",
};

/** Small square swatch used to key a category in legends and lists. */
export const CATEGORY_DOT_COLORS: Record<Topic["category"], string> = {
  core: "bg-indigo-500",
  applied: "bg-teal-500",
};

const CATEGORY_LABELS: Record<Topic["category"], string> = {
  core: "Core",
  applied: "Applied",
};

export function getCategoryLabel(category: Topic["category"]): string {
  return CATEGORY_LABELS[category];
}

export function getDefaultTopicConfig(): TopicConfig {
  const config: TopicConfig = {};
  for (const topic of TOPICS) {
    config[topic.id] = topic.defaultEnabled;
  }
  return config;
}

export function getActiveKeywords(config: TopicConfig): string[] {
  const keywords = new Set<string>();
  for (const topic of TOPICS) {
    if (config[topic.id]) {
      // Weak keywords are weak at *tagging*, not at filtering: the brand
      // names among them admit most of the Hacker News items that reach the
      // digest at all, so they belong in the active filter.
      for (const kw of [...topic.keywords, ...(topic.weakKeywords ?? [])]) {
        keywords.add(kw);
      }
    }
  }
  return [...keywords].sort();
}
