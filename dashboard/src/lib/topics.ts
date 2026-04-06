export interface Topic {
  id: string;
  name: string;
  description: string;
  category: "core" | "applied" | "emerging";
  keywords: string[];
  defaultEnabled: boolean;
}

export type TopicConfig = Record<string, boolean>;

export const TOPICS: Topic[] = [
  // Core
  {
    id: "models",
    name: "New Model Releases",
    description: "New models from major labs — GPT, Claude, Gemini, Llama, Mistral",
    category: "core",
    keywords: ["GPT", "Claude", "Gemini", "Llama", "Mistral", "model release"],
    defaultEnabled: true,
  },
  {
    id: "apis",
    name: "API & SDK Updates",
    description: "API changes, new SDK versions, breaking changes, deprecations",
    category: "core",
    keywords: ["API", "SDK", "endpoint", "breaking change", "deprecation"],
    defaultEnabled: true,
  },
  {
    id: "frameworks",
    name: "Dev Frameworks",
    description: "Updates to LangChain, LlamaIndex, AutoGen, CrewAI, and other frameworks",
    category: "core",
    keywords: ["LangChain", "LlamaIndex", "AutoGen", "CrewAI", "framework"],
    defaultEnabled: true,
  },
  // Applied
  {
    id: "inference",
    name: "Inference & Deployment",
    description: "vLLM, Ollama, TensorRT, quantization, model serving, deployment",
    category: "applied",
    keywords: ["vLLM", "Ollama", "TensorRT", "quantization", "serving", "deployment"],
    defaultEnabled: true,
  },
  {
    id: "finetuning",
    name: "Fine-tuning & Training",
    description: "Fine-tuning techniques, LoRA, QLoRA, Unsloth, PEFT, training tools",
    category: "applied",
    keywords: ["fine-tuning", "LoRA", "QLoRA", "Unsloth", "training", "PEFT"],
    defaultEnabled: true,
  },
  {
    id: "rag",
    name: "RAG & Memory",
    description: "Retrieval-augmented generation, vector databases, embeddings, memory systems",
    category: "applied",
    keywords: ["RAG", "retrieval", "vector database", "embedding", "memory"],
    defaultEnabled: true,
  },
  {
    id: "agents",
    name: "AI Agents",
    description: "Agent frameworks, tool use, multi-agent systems, autonomous agents",
    category: "applied",
    keywords: ["agent", "tool use", "multi-agent", "autonomous", "agentic"],
    defaultEnabled: true,
  },
  {
    id: "opensource",
    name: "Open Source Releases",
    description: "Notable open source and open weight model releases",
    category: "applied",
    keywords: ["open source", "open weights", "Apache", "MIT license"],
    defaultEnabled: true,
  },
  // Emerging
  {
    id: "safety",
    name: "Safety & Alignment",
    description: "AI safety research, alignment techniques, red-teaming, guardrails",
    category: "emerging",
    keywords: ["safety", "alignment", "jailbreak", "red-teaming", "guardrails"],
    defaultEnabled: true,
  },
  {
    id: "hardware",
    name: "Hardware & Efficiency",
    description: "GPU, TPU, custom chips, CUDA updates, inference cost optimization",
    category: "emerging",
    keywords: ["GPU", "TPU", "chip", "CUDA", "inference cost", "hardware"],
    defaultEnabled: false,
  },
];

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
