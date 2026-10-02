export interface Topic {
  id: string;
  name: string;
  description: string;
  category: "core" | "applied" | "emerging";
  keywords: string[];
  defaultEnabled: boolean;
}

// Persona: engineer/researcher tracking what the frontier AI labs ship.
// "core"     = primary daily reading (releases, product/API, research, agents, benchmarks, system cards)
// "applied"  = how the models get deployed and run
// "emerging" = surfaces that matter episodically

export type TopicConfig = Record<string, boolean>;

export const TOPICS: Topic[] = [
  // Core
  {
    id: "model_releases",
    name: "Model Releases",
    description: "New frontier models and versions from OpenAI, Anthropic, Google DeepMind, Meta, Mistral, xAI and others",
    category: "core",
    keywords: [
      "model release", "new model", "frontier model", "flagship model",
      "reasoning model", "model family", "introducing claude",
      "introducing gpt", "GPT-", "Claude", "Gemini", "Llama", "Mistral",
      "Qwen", "DeepSeek", "Grok", "Gemma", "Command R",
    ],
    defaultEnabled: true,
  },
  {
    id: "product_api",
    name: "Product & API",
    description: "AI API surfaces: batch and fine-tuning endpoints, context windows, token pricing",
    category: "core",
    // Mirrors src/topic_config.py. Generic terms were removed there because
    // they matched any software release ("public beta" admitted an
    // OpenStreetMap app; "SDK" admitted every client-library bump).
    keywords: [
      "batch api", "fine-tuning api", "responses api", "assistants api",
      "context window", "token pricing", "model deprecation",
    ],
    defaultEnabled: true,
  },
  {
    id: "lab_research",
    name: "Lab Research",
    description: "Technical reports and papers from lab research teams — scaling, pretraining, post-training, RL",
    category: "core",
    keywords: [
      "technical report", "research paper", "scaling law", "pretraining",
      "post-training", "reinforcement learning", "RLHF", "distillation",
      "mixture of experts", "chain of thought", "test-time compute",
      "long context", "sparse attention", "synthetic data",
    ],
    defaultEnabled: true,
  },
  {
    id: "agents_tooling",
    name: "Agents & Tooling",
    description: "Agentic systems, tool use, function calling, computer use, MCP, coding agents",
    category: "core",
    keywords: [
      "agentic", "AI agent", "tool use", "function calling",
      "computer use", "model context protocol", "MCP server",
      "coding agent", "browser agent", "multi-agent", "tool calling",
      "agent framework",
    ],
    defaultEnabled: true,
  },
  {
    id: "benchmarks",
    name: "Benchmarks & Evals",
    description: "Capability results and eval suites — SWE-bench, GPQA, ARC-AGI, AIME, FrontierMath, leaderboards",
    category: "core",
    keywords: [
      "benchmark", "evaluation suite", "SWE-bench", "GPQA",
      "ARC-AGI", "AIME", "FrontierMath", "MMLU", "leaderboard",
      "state of the art", "human evaluation", "model evaluation",
    ],
    defaultEnabled: true,
  },
  {
    id: "safety_system_cards",
    name: "Safety & System Cards",
    description: "System cards, responsible scaling and frontier safety frameworks, red-teaming, interpretability",
    category: "core",
    keywords: [
      "system card", "model card", "responsible scaling",
      "preparedness framework", "frontier safety", "red-teaming",
      "red teaming", "jailbreak", "prompt injection", "alignment",
      "interpretability", "safety evaluation",
    ],
    defaultEnabled: true,
  },
  // Applied
  {
    id: "open_weights",
    name: "Open Weights",
    description: "Open-weight model drops and their licenses — Llama, Mistral, Qwen, DeepSeek, Gemma, OLMo",
    category: "applied",
    keywords: [
      "open weights", "open-weight", "open source model", "open model",
      "weights release", "Apache 2.0", "model license",
      "Hugging Face release", "OLMo", "Gemma",
    ],
    defaultEnabled: true,
  },
  {
    id: "infrastructure",
    name: "Compute & Infrastructure",
    description: "Training and serving infrastructure — accelerators, clusters, inference stacks, quantization",
    category: "applied",
    keywords: [
      "inference", "quantization", "training run", "gpu cluster",
      "TPU", "Blackwell", "Trainium", "supercomputer", "datacenter",
      "serving", "kv cache", "throughput", "compute deal",
    ],
    defaultEnabled: true,
  },
  // Emerging
  {
    id: "multimodal",
    name: "Multimodal & Generative Media",
    description: "Vision, image, video, speech and world models shipped by the labs",
    category: "emerging",
    keywords: [
      "multimodal", "vision-language", "image generation",
      "video generation", "text-to-video", "speech model", "voice model",
      "text-to-speech", "world model", "diffusion model", "audio model",
    ],
    defaultEnabled: false,
  },
  {
    id: "enterprise_deployment",
    name: "Enterprise Deployment",
    description: "How labs land models in production — enterprise offerings, cloud partnerships, case studies",
    category: "emerging",
    keywords: [
      "enterprise", "deployment", "case study", "on-premise",
      "government deployment", "cloud partnership", "customer adoption",
      "production deployment", "compliance certification",
    ],
    defaultEnabled: false,
  },
  {
    id: "policy_regulation",
    name: "Policy & Regulation",
    description: "Rules that constrain what the labs can ship — EU AI Act, AISIs, export controls, compute governance",
    category: "emerging",
    keywords: [
      "EU AI Act", "AI regulation", "AI policy", "executive order",
      "AI safety institute", "AISI", "export controls",
      "compute governance", "AI legislation",
    ],
    defaultEnabled: false,
  },
];

/** Badge colors for category labels (used in history + stats pages) */
export const CATEGORY_BADGE_COLORS: Record<Topic["category"], string> = {
  core: "bg-blue-100 text-blue-800 dark:bg-blue-900/40 dark:text-blue-300",
  applied: "bg-purple-100 text-purple-800 dark:bg-purple-900/40 dark:text-purple-300",
  emerging: "bg-amber-100 text-amber-800 dark:bg-amber-900/40 dark:text-amber-300",
};

/** Progress bar fill colors (used in stats page) */
export const CATEGORY_BAR_COLORS: Record<Topic["category"], string> = {
  core: "bg-primary",
  applied: "bg-purple-500",
  emerging: "bg-amber-500",
};

/** Inline text colors for category tags (used in stats page) */
export const CATEGORY_TAG_COLORS: Record<Topic["category"], string> = {
  core: "text-blue-600 dark:text-blue-400",
  applied: "text-purple-600 dark:text-purple-400",
  emerging: "text-amber-600 dark:text-amber-400",
};

const CATEGORY_LABELS: Record<Topic["category"], string> = {
  core: "Core",
  applied: "Applied",
  emerging: "Emerging",
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
      for (const kw of topic.keywords) {
        keywords.add(kw);
      }
    }
  }
  return [...keywords].sort();
}
