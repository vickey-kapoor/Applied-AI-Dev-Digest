// Types
export interface Paper {
  id: string;
  title: string;
  description: string;
  source: string;
  url: string;
  published_at: string;
  fetched_at: string;
  authors: string;
  topics: string[];
  ranking_score: number;
  status: 'unread' | 'read' | 'starred';
}

export interface Digest {
  date: string;
  top_paper_id: string;
  papers_fetched: number;
  pdf_path: string;
  whatsapp_sent: boolean;
  workflow_run_id: string;
}

export interface Config {
  keywords: string[];
  sources: {
    arxiv: boolean;
    huggingface: boolean;
    pwc: boolean;
    blogs: boolean;
  };
  schedule: string;
  whatsapp_enabled: boolean;
}

// Inline data using JSON.parse to prevent any bundler optimization issues
const PAPERS_JSON = '{"papers":[{"id":"188557b2-8ba2-4533-8fc1-3df007d9566a","title":"The latest AI news we announced in February","description":"an MP4 of a carousel with images reading Gemini 3.1 Pro and Nano Banana 2","source":"Google AI","url":"https://blog.google/innovation-and-ai/products/google-ai-updates-february-2026/","published_at":"2026-03-05T16:30:00","fetched_at":"2026-03-08T00:21:13.285469Z","authors":"Google AI","topics":["Vision"],"ranking_score":0,"status":"unread"},{"id":"62b22d72-fedf-4bb0-bc0b-c619a7bcbd7f","title":"Interactive Benchmarks","description":"Standard benchmarks have become increasingly unreliable due to saturation, subjectivity, and poor generalization.","source":"Hugging Face","url":"https://huggingface.co/papers/2603.04737","published_at":"2026-03-05T02:18:26+00:00","fetched_at":"2026-03-08T00:21:13.285469Z","authors":"Baoqing Yue, Zihan Zhu, Yifan Zhang et al.","topics":["Reasoning"],"ranking_score":8.5,"status":"unread"},{"id":"254bc6b2-9f96-46ab-92b1-4181850a5d28","title":"Reasoning Theater: Disentangling Model Beliefs from Chain-of-Thought","description":"We provide evidence of performative chain-of-thought in reasoning models.","source":"arXiv","url":"https://arxiv.org/abs/2603.05488v1","published_at":"2026-03-05T00:00:00","fetched_at":"2026-03-08T00:21:13.285469Z","authors":"Siddharth Boppana, Annabel Ma, Max Loeffler et al.","topics":["Reasoning"],"ranking_score":0,"status":"unread"},{"id":"1deff0a4-3280-4433-b510-e22e8d34276b","title":"DEBISS: a Corpus of Individual, Semi-structured and Spoken Debates","description":"We address the scarcity of debate corpora by developing a dataset accounting for diverse debate formats.","source":"arXiv","url":"https://arxiv.org/abs/2603.04926v1","published_at":"2026-03-05T00:00:00","fetched_at":"2026-03-08T00:21:13.285469Z","authors":"Various","topics":["LLM"],"ranking_score":0,"status":"unread"},{"id":"paper5","title":"Multi-Agent Collaboration Framework","description":"A novel framework for enabling AI agents to collaborate on complex tasks.","source":"Hugging Face","url":"https://huggingface.co/papers/example5","published_at":"2026-03-05","fetched_at":"2026-03-08T00:21:13.285469Z","authors":"Research Team","topics":["AI Agent","Multi-Agent"],"ranking_score":0,"status":"unread"},{"id":"paper6","title":"Tool-Augmented Language Models","description":"Exploring how language models can effectively use external tools.","source":"arXiv","url":"https://arxiv.org/abs/example6","published_at":"2026-03-04","fetched_at":"2026-03-08T00:21:13.285469Z","authors":"AI Research Lab","topics":["Tool Use","LLM"],"ranking_score":0,"status":"unread"},{"id":"paper7","title":"Planning with Large Language Models","description":"A study on using LLMs for automated task planning and execution.","source":"Google AI","url":"https://blog.google/example7","published_at":"2026-03-04","fetched_at":"2026-03-08T00:21:13.285469Z","authors":"Google Research","topics":["Planning","AI Agent"],"ranking_score":0,"status":"unread"},{"id":"paper8","title":"Chain-of-Thought Prompting Advances","description":"New techniques for improving reasoning through chain-of-thought prompting.","source":"arXiv","url":"https://arxiv.org/abs/example8","published_at":"2026-03-04","fetched_at":"2026-03-08T00:21:13.285469Z","authors":"University Research","topics":["Reasoning"],"ranking_score":0,"status":"unread"},{"id":"paper9","title":"Autonomous Agent Architectures","description":"A comprehensive survey of autonomous agent architectures in AI systems.","source":"Hugging Face","url":"https://huggingface.co/papers/example9","published_at":"2026-03-03","fetched_at":"2026-03-08T00:21:13.285469Z","authors":"Survey Authors","topics":["AI Agent"],"ranking_score":0,"status":"unread"},{"id":"paper10","title":"Vision-Language Models for Robotics","description":"Applying vision-language models to robotic manipulation tasks.","source":"DeepMind","url":"https://deepmind.google/example10","published_at":"2026-03-03","fetched_at":"2026-03-08T00:21:13.285469Z","authors":"DeepMind Team","topics":["Vision","AI Agent"],"ranking_score":0,"status":"unread"}]}';

const DIGESTS_JSON = '{"digests":[{"date":"2026-03-08","top_paper_id":"62b22d72-fedf-4bb0-bc0b-c619a7bcbd7f","papers_fetched":10,"pdf_path":"reports/07-Mar/Interactive_Benchmarks.pdf","whatsapp_sent":true,"workflow_run_id":""}]}';

const CONFIG_JSON = '{"keywords":["AI agent","autonomous agent","reasoning","chain of thought","CoT","ReAct","tool use","planning","multi-agent","agentic"],"sources":{"arxiv":true,"huggingface":true,"pwc":true,"blogs":true},"schedule":"0 16 * * *","whatsapp_enabled":true}';

// Parse at module load time
let _papers: Paper[] | null = null;
let _digests: Digest[] | null = null;
let _config: Config | null = null;

export function getPapers(): Paper[] {
  if (_papers === null) {
    try {
      const parsed = JSON.parse(PAPERS_JSON);
      _papers = parsed.papers as Paper[];
      console.log('[DATA] Parsed papers from JSON string, count:', _papers.length);
    } catch (e) {
      console.error('[DATA] Failed to parse PAPERS_JSON:', e);
      _papers = [];
    }
  }
  console.log('[DATA] getPapers returning:', _papers.length);
  return _papers;
}

export function getDigests(): Digest[] {
  if (_digests === null) {
    try {
      const parsed = JSON.parse(DIGESTS_JSON);
      _digests = parsed.digests as Digest[];
      console.log('[DATA] Parsed digests from JSON string, count:', _digests.length);
    } catch (e) {
      console.error('[DATA] Failed to parse DIGESTS_JSON:', e);
      _digests = [];
    }
  }
  return _digests;
}

export function getConfig(): Config {
  if (_config === null) {
    try {
      _config = JSON.parse(CONFIG_JSON) as Config;
    } catch (e) {
      console.error('[DATA] Failed to parse CONFIG_JSON:', e);
      _config = {
        keywords: [],
        sources: { arxiv: true, huggingface: true, pwc: true, blogs: true },
        schedule: "0 16 * * *",
        whatsapp_enabled: true
      };
    }
  }
  return _config;
}

export function getReportDates(): string[] {
  const digests = getDigests();
  const dates = digests
    .filter(d => d.pdf_path)
    .map(d => {
      const match = d.pdf_path.match(/reports[\/\\]([^\/\\]+)[\/\\]/);
      return match ? match[1] : null;
    })
    .filter((date): date is string => date !== null);

  return [...new Set(dates)].sort().reverse();
}

export function getStats() {
  const papers = getPapers();
  const digests = getDigests();

  const today = new Date().toISOString().split('T')[0];
  const todaysPapers = papers.filter(p => p.fetched_at?.startsWith(today));
  const todaysDigest = digests.find(d => d.date === today);

  const sourceCounts = papers.reduce((acc, p) => {
    acc[p.source] = (acc[p.source] || 0) + 1;
    return acc;
  }, {} as Record<string, number>);

  return {
    totalPapers: papers.length,
    todaysPapers: todaysPapers.length,
    totalDigests: digests.length,
    todaysDigest,
    sourceCounts,
    unreadCount: papers.filter(p => p.status === 'unread').length,
    starredCount: papers.filter(p => p.status === 'starred').length,
  };
}
