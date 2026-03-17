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
  telegram_sent: boolean;
  workflow_run_id: string;
}

export interface Config {
  keywords: string[];
  sources: {
    blogs: boolean;
  };
  labs: string[];
  schedule: string;
  telegram_enabled: boolean;
}

const DEFAULT_REPO = 'vickey-kapoor/ai-research-digest';
const DEFAULT_BRANCHES = ['master', 'main'];

function splitBranches(value: string | undefined): string[] {
  if (!value) return DEFAULT_BRANCHES;

  const branches = value
    .split(',')
    .map((branch) => branch.trim())
    .filter(Boolean);

  return branches.length > 0 ? [...new Set(branches)] : DEFAULT_BRANCHES;
}

export function getRepoConfig() {
  const repo =
    process.env.AI_RESEARCH_REPO ||
    process.env.NEXT_PUBLIC_AI_RESEARCH_REPO ||
    DEFAULT_REPO;

  const branches = splitBranches(
    process.env.AI_RESEARCH_BRANCHES ||
    process.env.NEXT_PUBLIC_AI_RESEARCH_BRANCHES
  );

  return { repo, branches };
}

async function fetchJSON(path: string): Promise<unknown> {
  const { repo, branches } = getRepoConfig();

  for (const branch of branches) {
    const res = await fetch(`https://raw.githubusercontent.com/${repo}/${branch}/${path}`, {
      next: { revalidate: 300 }, // ISR: refresh every 5 minutes
    });
    if (res.ok) {
      return res.json();
    }
  }

  return null;
}

export async function getPapers(): Promise<Paper[]> {
  try {
    const data = await fetchJSON('data/papers.json') as { papers: Paper[] } | null;
    return data?.papers ?? [];
  } catch (e) {
    console.error('[DATA] Failed to fetch papers:', e);
    return [];
  }
}

export async function getDigests(): Promise<Digest[]> {
  try {
    const data = await fetchJSON('data/digests.json') as { digests: Digest[] } | null;
    return data?.digests ?? [];
  } catch (e) {
    console.error('[DATA] Failed to fetch digests:', e);
    return [];
  }
}

export function getConfig(): Config {
  return {
    keywords: [
      "API", "SDK", "model release", "new feature", "changelog",
      "launch", "developer tools", "fine-tuning", "embeddings",
      "function calling", "multimodal", "context window"
    ],
    sources: { blogs: true },
    labs: ["OpenAI", "Anthropic", "Google DeepMind", "Meta AI"],
    schedule: "0 16 * * *",
    telegram_enabled: true,
  };
}

export async function getBacklog() {
  const papers = await getPapers();

  // Only unread/starred items go into the backlog (things to try)
  const backlogItems = papers.filter(p => p.status === 'unread' || p.status === 'starred');

  // Group by lab (source)
  const grouped = backlogItems.reduce((acc, paper) => {
    const lab = paper.source || 'Unknown';
    if (!acc[lab]) acc[lab] = [];
    acc[lab].push(paper);
    return acc;
  }, {} as Record<string, Paper[]>);

  // Sort each lab's items by date descending
  for (const lab of Object.keys(grouped)) {
    grouped[lab].sort((a, b) => (b.published_at || '').localeCompare(a.published_at || ''));
  }

  return grouped;
}

export async function getReportDates(): Promise<string[]> {
  const digests = await getDigests();
  const dates = digests
    .filter(d => d.pdf_path)
    .map(d => {
      const match = d.pdf_path.match(/reports[\/\\]([^\/\\]+)[\/\\]/);
      return match ? match[1] : null;
    })
    .filter((date): date is string => date !== null);

  return [...new Set(dates)].sort().reverse();
}

export async function getStats() {
  const papers = await getPapers();
  const digests = await getDigests();

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
