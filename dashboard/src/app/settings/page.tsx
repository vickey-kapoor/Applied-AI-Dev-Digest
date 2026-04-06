import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import {
  Settings as SettingsIcon,
  Database,
  Clock,
  Send,
  Github,
  ExternalLink,
  Newspaper,
} from "lucide-react";

const BLOG_SOURCES = [
  "OpenAI",
  "Anthropic",
  "Google DeepMind",
  "Meta AI",
  "Mistral",
  "Microsoft AI",
  "AWS AI",
  "Hugging Face",
];

const GITHUB_REPOS = [
  "huggingface/transformers",
  "langchain-ai/langchain",
  "run-llama/llama_index",
  "vllm-project/vllm",
  "ollama/ollama",
  "openai/openai-python",
  "anthropics/anthropic-sdk-python",
  "microsoft/autogen",
  "unsloth/unsloth",
  "ggerganov/llama.cpp",
];

export default function SettingsPage() {
  return (
    <div className="py-8">
      <div className="mb-8">
        <div className="flex items-baseline gap-3 mb-1">
          <SettingsIcon className="h-7 w-7 text-primary shrink-0 self-center" />
          <h1 className="text-2xl font-display font-bold text-foreground">Settings</h1>
        </div>
        <p className="text-muted-foreground mt-1">Pipeline configuration and integrations</p>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Blog Sources */}
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <Database className="h-5 w-5 text-green-600" />
              Blog Sources
            </CardTitle>
            <CardDescription>AI lab and platform blogs being monitored</CardDescription>
          </CardHeader>
          <CardContent>
            <div className="flex flex-wrap gap-2">
              {BLOG_SOURCES.map((lab) => (
                <Badge key={lab} variant="secondary" className="text-sm">
                  {lab}
                </Badge>
              ))}
            </div>
            <p className="text-xs text-muted-foreground/70 mt-4">
              Configured in <code className="bg-secondary px-1 rounded font-mono">src/constants.py</code>
            </p>
          </CardContent>
        </Card>

        {/* GitHub Repos */}
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <Github className="h-5 w-5 text-foreground" />
              GitHub Releases
            </CardTitle>
            <CardDescription>Repos tracked for new releases</CardDescription>
          </CardHeader>
          <CardContent>
            <div className="flex flex-wrap gap-2">
              {GITHUB_REPOS.map((repo) => (
                <a
                  key={repo}
                  href={`https://github.com/${repo}`}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="inline-flex items-center gap-1"
                >
                  <Badge variant="outline" className="text-sm hover:bg-secondary transition-colors cursor-pointer">
                    {repo.split("/")[1]}
                  </Badge>
                </a>
              ))}
            </div>
            <p className="text-xs text-muted-foreground/70 mt-4">
              Releases fetched via GitHub API (skips pre-releases, 48h window)
            </p>
          </CardContent>
        </Card>

        {/* Hacker News */}
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <Newspaper className="h-5 w-5 text-orange-600" />
              Hacker News
            </CardTitle>
            <CardDescription>AI/ML discussions from HN</CardDescription>
          </CardHeader>
          <CardContent>
            <div className="space-y-3">
              <div className="flex items-center justify-between">
                <span className="text-sm text-muted-foreground">Min score</span>
                <span className="font-mono font-medium">100+</span>
              </div>
              <div className="flex items-center justify-between">
                <span className="text-sm text-muted-foreground">Max stories</span>
                <span className="font-mono font-medium">5</span>
              </div>
              <div className="flex items-center justify-between">
                <span className="text-sm text-muted-foreground">Recency</span>
                <span className="font-mono font-medium">Last 24h</span>
              </div>
            </div>
          </CardContent>
        </Card>

        {/* Schedule */}
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <Clock className="h-5 w-5 text-orange-600" />
              Schedule
            </CardTitle>
            <CardDescription>When the digest runs</CardDescription>
          </CardHeader>
          <CardContent>
            <div className="space-y-3">
              <div>
                <p className="text-sm text-muted-foreground">Cron Expression</p>
                <p className="font-mono text-lg">0 16 * * *</p>
              </div>
              <div>
                <p className="text-sm text-muted-foreground">Human Readable</p>
                <p className="font-medium">Daily at 10:00 AM CST (16:00 UTC)</p>
              </div>
              <a
                href="https://crontab.guru/#0_16_*_*_*"
                target="_blank"
                rel="noopener noreferrer"
                className="text-sm text-primary hover:underline inline-flex items-center gap-1"
              >
                View on crontab.guru
                <ExternalLink className="h-3 w-3" />
              </a>
            </div>
          </CardContent>
        </Card>

        {/* Telegram */}
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <Send className="h-5 w-5 text-primary" />
              Telegram
            </CardTitle>
            <CardDescription>Message delivery</CardDescription>
          </CardHeader>
          <CardContent>
            <div className="space-y-3">
              <div className="flex items-center justify-between">
                <span className="font-medium">Status</span>
                <Badge variant="success">Enabled</Badge>
              </div>
              <div>
                <p className="text-sm text-muted-foreground">Format</p>
                <p className="font-medium">Structured Dev Summary (Why / What / How / Take)</p>
              </div>
            </div>
          </CardContent>
        </Card>

        {/* GitHub Actions */}
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <Github className="h-5 w-5 text-foreground" />
              GitHub Actions
            </CardTitle>
            <CardDescription>Workflow automation</CardDescription>
          </CardHeader>
          <CardContent>
            <div className="space-y-4">
              <div>
                <p className="text-sm text-muted-foreground mb-1">Workflow</p>
                <code className="text-sm font-mono bg-secondary px-2 py-1 rounded">
                  .github/workflows/daily-news.yml
                </code>
              </div>
              <div>
                <p className="text-sm text-muted-foreground mb-1">Repository</p>
                <a
                  href="https://github.com/vickey-kapoor/ai-research-digest"
                  target="_blank"
                  rel="noopener noreferrer"
                  className="text-primary hover:underline inline-flex items-center gap-1 text-sm"
                >
                  vickey-kapoor/ai-research-digest
                  <ExternalLink className="h-3.5 w-3.5" />
                </a>
              </div>
              <a
                href="https://github.com/vickey-kapoor/ai-research-digest/actions/workflows/daily-news.yml"
                target="_blank"
                rel="noopener noreferrer"
                className="inline-flex items-center gap-2 px-4 py-2 bg-gray-900 dark:bg-gray-100 text-white dark:text-gray-900 rounded-lg hover:bg-gray-800 dark:hover:bg-gray-200 transition-colors text-sm"
              >
                <Github className="h-4 w-4" />
                Run Workflow on GitHub
              </a>
            </div>
          </CardContent>
        </Card>
      </div>

      {/* KV info banner */}
      <div className="mt-8 p-4 bg-primary/10 rounded-lg border border-primary/20">
        <div className="flex items-start gap-3">
          <SettingsIcon className="h-5 w-5 text-primary mt-0.5" />
          <div>
            <p className="font-medium text-foreground">KV Storage</p>
            <p className="text-sm text-muted-foreground mt-1">
              Topics, pause state, and stats are stored in Vercel KV (Upstash Redis).
              Set <code className="bg-primary/15 px-1 rounded font-mono">KV_REST_API_URL</code> and{" "}
              <code className="bg-primary/15 px-1 rounded font-mono">KV_REST_API_TOKEN</code> in
              both Vercel and GitHub Secrets.
            </p>
          </div>
        </div>
      </div>
    </div>
  );
}
