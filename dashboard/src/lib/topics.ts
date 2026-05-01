export interface Topic {
  id: string;
  name: string;
  description: string;
  category: "core" | "applied" | "emerging";
  keywords: string[];
  defaultEnabled: boolean;
}

// Persona: AI Safety researcher.
// "core"     = primary daily reading (alignment, interp, evals, red-teaming, system cards, agentic safety)
// "applied"  = governance + downstream risk surfaces
// "emerging" = robustness, data provenance, open-weights safety

export type TopicConfig = Record<string, boolean>;

export const TOPICS: Topic[] = [
  // Core
  {
    id: "alignment",
    name: "Alignment Techniques",
    description: "RLHF, RLAIF, DPO, Constitutional AI, scalable oversight, debate, reward modeling",
    category: "core",
    keywords: [
      "RLHF", "RLAIF", "DPO", "constitutional AI", "scalable oversight",
      "weak-to-weak", "weak-to-strong", "debate", "recursive reward",
      "instruction tuning", "alignment", "preference learning",
      "reward model", "reward hacking",
    ],
    defaultEnabled: true,
  },
  {
    id: "interpretability",
    name: "Interpretability",
    description: "Mechanistic interpretability, sparse autoencoders, circuits, probing, activation steering",
    category: "core",
    keywords: [
      "interpretability", "mechanistic interpretability", "mech interp",
      "sparse autoencoder", "SAE", "circuit analysis", "feature attribution",
      "probing", "activation steering", "activation patching",
      "logit lens", "TransformerLens", "sae_lens", "monosemanticity",
    ],
    defaultEnabled: true,
  },
  {
    id: "evals",
    name: "Evals & Benchmarks",
    description: "Capability evals, dangerous-capability evals, autonomy evals, inspect_ai, METR-style work",
    category: "core",
    keywords: [
      "benchmark", "eval", "evaluation suite", "capability eval",
      "dangerous capability", "autonomy eval", "MMLU", "BIG-bench",
      "HELM", "inspect_ai", "METR", "GPQA", "ARC-AGI", "SWE-bench",
      "model evaluation",
    ],
    defaultEnabled: true,
  },
  {
    id: "red_teaming",
    name: "Red-teaming & Jailbreaks",
    description: "Adversarial attacks, jailbreak techniques, automated red-teaming, prompt injection",
    category: "core",
    keywords: [
      "red-teaming", "red teaming", "jailbreak", "prompt injection",
      "adversarial prompt", "automated red-teaming", "PAIR attack",
      "GCG attack", "universal adversarial", "garak", "harm bench",
    ],
    defaultEnabled: true,
  },
  {
    id: "system_cards",
    name: "Model & System Cards",
    description: "Frontier-model release safety reports — RSPs, preparedness frameworks, deployment evals",
    category: "core",
    keywords: [
      "system card", "model card", "responsible scaling policy", "RSP",
      "preparedness framework", "frontier safety", "release notes safety",
      "deployment evaluation",
    ],
    defaultEnabled: true,
  },
  {
    id: "agentic_safety",
    name: "Agentic Safety",
    description: "Deception, scheming, sandbagging, situational awareness, alignment faking, sabotage evals",
    category: "core",
    keywords: [
      "deception", "scheming", "sandbagging", "situational awareness",
      "alignment faking", "sabotage", "agent safety", "autonomous agent risk",
      "agent evaluation", "in-context scheming",
    ],
    defaultEnabled: true,
  },
  // Applied
  {
    id: "governance",
    name: "Governance & Policy",
    description: "NIST AISI, UK AISI, EU AI Act, executive orders, compute governance, RSPs",
    category: "applied",
    keywords: [
      "NIST AISI", "UK AISI", "EU AI Act", "AI safety institute",
      "executive order", "compute governance", "frontier AI", "AI policy",
      "AI regulation", "responsible scaling",
    ],
    defaultEnabled: false,
  },
  {
    id: "catastrophic_risk",
    name: "Catastrophic Risk",
    description: "CBRN uplift, biorisk, cyber uplift, persuasion studies, WMDP",
    category: "applied",
    keywords: [
      "CBRN", "biorisk", "bioweapon", "chemical weapon", "cyber uplift",
      "persuasion", "manipulation", "catastrophic risk", "existential risk",
      "WMDP", "uplift study",
    ],
    defaultEnabled: false,
  },
  // Emerging
  {
    id: "robustness",
    name: "Robustness & Adversarial ML",
    description: "Adversarial examples, distribution shift, OOD generalization, calibration",
    category: "emerging",
    keywords: [
      "adversarial example", "distribution shift", "out-of-distribution",
      "OOD", "robustness", "adversarial robustness", "spurious correlation",
      "calibration",
    ],
    defaultEnabled: false,
  },
  {
    id: "data_provenance",
    name: "Training Data & Provenance",
    description: "Data poisoning, watermarking, data attribution, memorization, extraction attacks",
    category: "emerging",
    keywords: [
      "data poisoning", "watermarking", "model watermark", "training data",
      "data attribution", "membership inference", "memorization",
      "data extraction", "provenance",
    ],
    defaultEnabled: false,
  },
  {
    id: "open_weights_safety",
    name: "Open-Weights Safety",
    description: "Safety implications of open-weight releases, fine-tuning attacks, removable safety",
    category: "emerging",
    keywords: [
      "open weights", "open-source model", "fine-tuning attack",
      "safety finetuning", "removable safety", "Llama 3", "Mistral", "Qwen",
      "DeepSeek",
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
