import { promises as fs } from 'fs';
import path from 'path';

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

// GitHub raw content URL for fetching data in production
const GITHUB_RAW_BASE = 'https://raw.githubusercontent.com/vickey-kapoor/ai-research-whatsapp-digest/master/data';

// Data file paths (relative to dashboard root, then project root)
const DATA_PATHS = [
  path.join(process.cwd(), 'data'),           // dashboard/data (for Vercel)
  path.join(process.cwd(), '..', 'data'),     // ../data (for local dev)
];

async function readJsonFile(filename: string): Promise<unknown | null> {
  // Try local paths first
  for (const dataPath of DATA_PATHS) {
    try {
      const filePath = path.join(dataPath, filename);
      const data = await fs.readFile(filePath, 'utf-8');
      return JSON.parse(data);
    } catch {
      // Continue to next path
    }
  }

  // Fall back to GitHub raw content (for Vercel deployment)
  try {
    const response = await fetch(`${GITHUB_RAW_BASE}/${filename}`, {
      next: { revalidate: 300 } // Revalidate every 5 minutes
    });
    if (response.ok) {
      return await response.json();
    }
  } catch {
    // Failed to fetch from GitHub
  }

  return null;
}

export async function getPapers(): Promise<Paper[]> {
  const data = await readJsonFile('papers.json') as { papers?: Paper[] } | null;
  return data?.papers || [];
}

export async function getDigests(): Promise<Digest[]> {
  const data = await readJsonFile('digests.json') as { digests?: Digest[] } | null;
  return data?.digests || [];
}

export async function getConfig(): Promise<Config> {
  const data = await readJsonFile('config.json') as Config | null;

  // Return fetched config or default
  return data || {
    keywords: [
      'AI agent', 'autonomous agent', 'reasoning', 'chain of thought',
      'CoT', 'ReAct', 'tool use', 'planning', 'multi-agent', 'agentic'
    ],
    sources: {
      arxiv: true,
      huggingface: true,
      pwc: true,
      blogs: true
    },
    schedule: '0 16 * * *',
    whatsapp_enabled: true
  };
}

export async function getReportDates(): Promise<string[]> {
  // Try local paths first
  const reportPaths = [
    path.join(process.cwd(), 'reports'),
    path.join(process.cwd(), '..', 'reports'),
  ];

  for (const reportsDir of reportPaths) {
    try {
      const entries = await fs.readdir(reportsDir, { withFileTypes: true });
      return entries
        .filter(entry => entry.isDirectory())
        .map(entry => entry.name)
        .sort()
        .reverse();
    } catch {
      // Continue to next path
    }
  }

  // For Vercel, we can derive report dates from digests
  const digests = await getDigests();
  const dates = digests
    .filter(d => d.pdf_path)
    .map(d => {
      // Extract date folder from pdf_path like "reports/07-Mar/ai_research_digest.pdf"
      const match = d.pdf_path.match(/reports\/([^/]+)\//);
      return match ? match[1] : null;
    })
    .filter((date): date is string => date !== null);

  return [...new Set(dates)].sort().reverse();
}

// Stats helpers
export async function getStats() {
  const papers = await getPapers();
  const digests = await getDigests();

  const today = new Date().toISOString().split('T')[0];
  const todaysPapers = papers.filter(p => p.fetched_at.startsWith(today));
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
