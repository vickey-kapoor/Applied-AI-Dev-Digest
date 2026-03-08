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

// Import data directly from public folder
import papersData from '../../public/data/papers.json';
import digestsData from '../../public/data/digests.json';
import configData from '../../public/data/config.json';

export async function getPapers(): Promise<Paper[]> {
  return (papersData as { papers: Paper[] }).papers || [];
}

export async function getDigests(): Promise<Digest[]> {
  return (digestsData as { digests: Digest[] }).digests || [];
}

export async function getConfig(): Promise<Config> {
  return configData as Config;
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

// Stats helpers
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
