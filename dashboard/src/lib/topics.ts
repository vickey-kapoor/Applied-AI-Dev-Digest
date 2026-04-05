export interface Topic {
  id: string;
  name: string;
  description: string;
  category: "core" | "applied" | "emerging";
  keywords: string[];
  arxivCategories: string[];
  defaultEnabled: boolean;
}

export type TopicConfig = Record<string, boolean>;

export const TOPICS: Topic[] = [
  // Core
  {
    id: "agents",
    name: "AI Agents & Tool Use",
    description: "Autonomous agents, tool integration, and multi-agent collaboration",
    category: "core",
    keywords: ["agent", "tool use", "multi-agent", "agentic", "function calling"],
    arxivCategories: ["cs.AI", "cs.MA"],
    defaultEnabled: true,
  },
  {
    id: "reasoning",
    name: "Reasoning & Planning",
    description: "Chain-of-thought, step-by-step reasoning, and planning capabilities",
    category: "core",
    keywords: ["reasoning", "chain-of-thought", "planning"],
    arxivCategories: ["cs.AI", "cs.LG"],
    defaultEnabled: true,
  },
  {
    id: "alignment",
    name: "LLM Fine-tuning & Alignment",
    description: "RLHF, DPO, instruction tuning, and model alignment techniques",
    category: "core",
    keywords: ["rlhf", "dpo", "instruction tuning", "alignment", "fine-tuning", "fine-tune"],
    arxivCategories: ["cs.CL", "cs.LG"],
    defaultEnabled: true,
  },
  // Applied Domains
  {
    id: "codegen",
    name: "Code Generation & Dev Tools",
    description: "AI-powered code generation, program synthesis, and developer tooling",
    category: "applied",
    keywords: ["code generation", "program synthesis", "coding assistant", "developer tools", "cli", "sdk", "api", "endpoint", "playground", "library"],
    arxivCategories: ["cs.SE", "cs.PL"],
    defaultEnabled: true,
  },
  {
    id: "science",
    name: "AI for Science",
    description: "Drug discovery, materials science, protein folding, and molecular research",
    category: "applied",
    keywords: ["drug discovery", "materials science", "protein", "molecular"],
    arxivCategories: ["cs.LG", "q-bio"],
    defaultEnabled: true,
  },
  {
    id: "multimodal",
    name: "Multimodal AI",
    description: "Vision-language models, audio processing, and cross-modal reasoning",
    category: "applied",
    keywords: ["multimodal", "vision-language", "vlm", "audio"],
    arxivCategories: ["cs.CV", "cs.CL"],
    defaultEnabled: false,
  },
  {
    id: "robotics",
    name: "Robotics & Embodied AI",
    description: "Robot learning, manipulation, sim-to-real transfer, and embodied agents",
    category: "applied",
    keywords: ["robotics", "embodied", "manipulation", "sim-to-real"],
    arxivCategories: ["cs.RO"],
    defaultEnabled: false,
  },
  {
    id: "healthcare",
    name: "AI in Healthcare",
    description: "Medical AI, clinical decision support, and diagnostic systems",
    category: "applied",
    keywords: ["healthcare", "medical", "clinical", "diagnostics"],
    arxivCategories: ["cs.AI", "cs.LG"],
    defaultEnabled: true,
  },
  {
    id: "finance",
    name: "AI for Finance",
    description: "Trading algorithms, financial forecasting, and risk assessment",
    category: "applied",
    keywords: ["finance", "trading", "forecasting", "risk"],
    arxivCategories: ["cs.LG", "q-fin"],
    defaultEnabled: false,
  },
  {
    id: "nlp",
    name: "NLP & Language Understanding",
    description: "Summarization, translation, dialogue systems, and text understanding",
    category: "applied",
    keywords: ["nlp", "summarization", "translation", "dialogue"],
    arxivCategories: ["cs.CL"],
    defaultEnabled: false,
  },
  // Emerging
  {
    id: "safety",
    name: "AI Safety & Interpretability",
    description: "Mechanistic interpretability, red-teaming, and AI safety research",
    category: "emerging",
    keywords: ["safety", "interpretability", "mechanistic", "red-teaming"],
    arxivCategories: ["cs.AI", "cs.LG"],
    defaultEnabled: true,
  },
  {
    id: "efficient",
    name: "Efficient Inference",
    description: "Quantization, distillation, speculative decoding, and MoE architectures",
    category: "emerging",
    keywords: ["quantization", "distillation", "speculative decoding", "moe"],
    arxivCategories: ["cs.LG", "cs.AR"],
    defaultEnabled: false,
  },
  {
    id: "synthetic",
    name: "Synthetic Data & Self-play",
    description: "Synthetic data generation, self-play training, and self-improvement loops",
    category: "emerging",
    keywords: ["synthetic data", "self-play", "self-improvement"],
    arxivCategories: ["cs.LG", "cs.AI"],
    defaultEnabled: false,
  },
];

const CATEGORY_LABELS: Record<Topic["category"], string> = {
  core: "Core",
  applied: "Applied Domains",
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

export function getActiveArxivCategories(config: TopicConfig): string[] {
  const categories = new Set<string>();
  for (const topic of TOPICS) {
    if (config[topic.id]) {
      for (const cat of topic.arxivCategories) {
        categories.add(cat);
      }
    }
  }
  return [...categories].sort();
}
