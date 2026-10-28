import * as React from "react";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { PageHeader } from "@/components/ui/page-header";
import { buttonVariants } from "@/components/ui/button";
import { cn } from "@/lib/utils";
import {
  Settings as SettingsIcon,
  Database,
  Clock,
  Send,
  ExternalLink,
  Newspaper,
  BookOpen,
  Info,
  type LucideIcon,
} from "lucide-react";
import { GithubIcon } from "@/components/icons/github";

// Mirrors BLOG_FEEDS in src/constants.py
const BLOG_SOURCES = [
  "OpenAI",
  "Google DeepMind",
  "Google AI",
  "Google Research",
  "Meta AI",
  "Mistral AI",
  "Hugging Face Blog",
  "NVIDIA",
  "Together AI",
];

// Mirrors GITHUB_REPOS in src/constants.py
const GITHUB_REPOS = [
  "openai/openai-python",
  "anthropics/anthropic-sdk-python",
  "googleapis/python-genai",
  "huggingface/transformers",
  "vllm-project/vllm",
  "ggml-org/llama.cpp",
  "modelcontextprotocol/servers",
];

/** Icon tile shared by every settings card header. */
function CardIcon({
  icon: Icon,
}: {
  icon: LucideIcon | ((props: { className?: string }) => React.ReactElement);
}) {
  return (
    <span className="flex h-8 w-8 shrink-0 items-center justify-center rounded-lg border border-border bg-surface text-muted-foreground">
      <Icon className="h-4 w-4" />
    </span>
  );
}

/** A label/value line, used for the numeric thresholds. */
function Row({ label, value }: { label: string; value: React.ReactNode }) {
  return (
    <div className="flex items-center justify-between gap-4 border-b border-border py-2.5 last:border-0 last:pb-0">
      <span className="text-sm text-muted-foreground">{label}</span>
      <span className="font-mono text-sm font-medium text-foreground">
        {value}
      </span>
    </div>
  );
}

export default function SettingsPage() {
  return (
    <div className="pb-20">
      <PageHeader
        eyebrow="Pipeline"
        title="Settings"
        description="What the digest reads, how it ranks, and where it delivers. Source configuration lives in the repository."
        icon={SettingsIcon}
        actions={
          <a
            href="https://github.com/vickey-kapoor/Applied-AI-Dev-Digest/actions/workflows/daily-news.yml"
            target="_blank"
            rel="noopener noreferrer"
            className={cn(buttonVariants({ variant: "solid", size: "lg" }))}
          >
            <GithubIcon className="h-4 w-4" />
            Run workflow
          </a>
        }
      />

      {/* No items-start: the cards stretch so each row shares one height. */}
      <div className="mt-8 grid grid-cols-1 gap-4 md:grid-cols-2 xl:grid-cols-3">
        {/* Blog Sources */}
        <Card interactive className="flex flex-col">
          <CardHeader className="min-h-[5.5rem] flex-row items-center gap-3 space-y-0">
            <CardIcon icon={Database} />
            <div className="min-w-0">
              <CardTitle>Blog sources</CardTitle>
              <CardDescription>
                AI lab and platform blogs being monitored
              </CardDescription>
            </div>
          </CardHeader>
          <CardContent className="flex flex-1 flex-col">
            <div className="flex flex-wrap gap-1.5">
              {BLOG_SOURCES.map((lab) => (
                <Badge key={lab} variant="secondary">
                  {lab}
                </Badge>
              ))}
            </div>
            <p className="mt-auto pt-4 text-xs text-subtle-foreground">
              Configured in{" "}
              <code className="rounded bg-secondary px-1.5 py-0.5 font-mono text-foreground">
                src/constants.py
              </code>
            </p>
          </CardContent>
        </Card>

        {/* GitHub Repos */}
        <Card interactive className="flex flex-col">
          <CardHeader className="min-h-[5.5rem] flex-row items-center gap-3 space-y-0">
            <CardIcon icon={GithubIcon} />
            <div className="min-w-0">
              <CardTitle>GitHub releases</CardTitle>
              <CardDescription>Repos tracked for new releases</CardDescription>
            </div>
          </CardHeader>
          <CardContent className="flex flex-1 flex-col">
            <div className="flex flex-wrap gap-1.5">
              {GITHUB_REPOS.map((repo) => (
                <a
                  key={repo}
                  href={`https://github.com/${repo}`}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="rounded-md"
                >
                  <Badge variant="outline" className="font-mono">
                    {repo.split("/")[1]}
                  </Badge>
                </a>
              ))}
            </div>
            <p className="mt-auto pt-4 text-xs text-subtle-foreground">
              Fetched via the GitHub API — pre-releases skipped, 48h window.
            </p>
          </CardContent>
        </Card>

        {/* HF Daily Papers */}
        <Card interactive className="flex flex-col">
          <CardHeader className="min-h-[5.5rem] flex-row items-center gap-3 space-y-0">
            <CardIcon icon={BookOpen} />
            <div className="min-w-0">
              <CardTitle>HF daily papers</CardTitle>
              <CardDescription>
                Trending papers from Hugging Face
              </CardDescription>
            </div>
          </CardHeader>
          <CardContent className="flex flex-1 flex-col">
            <Row label="Min upvotes" value="20+" />
            <Row label="Max papers" value="5" />
            <Row label="Recency" value="Last 24h" />
          </CardContent>
        </Card>

        {/* Hacker News */}
        <Card interactive className="flex flex-col">
          <CardHeader className="min-h-[5.5rem] flex-row items-center gap-3 space-y-0">
            <CardIcon icon={Newspaper} />
            <div className="min-w-0">
              <CardTitle>Hacker News</CardTitle>
              <CardDescription>Frontier lab discussions from HN</CardDescription>
            </div>
          </CardHeader>
          <CardContent className="flex flex-1 flex-col">
            <Row label="Min score" value="100+" />
            <Row label="Max stories" value="5" />
            <Row label="Recency" value="Last 24h" />
          </CardContent>
        </Card>

        {/* Schedule */}
        <Card interactive className="flex flex-col">
          <CardHeader className="min-h-[5.5rem] flex-row items-center gap-3 space-y-0">
            <CardIcon icon={Clock} />
            <div className="min-w-0">
              <CardTitle>Schedule</CardTitle>
              <CardDescription>When the digest runs</CardDescription>
            </div>
          </CardHeader>
          <CardContent className="flex flex-1 flex-col">
            <div className="rounded-lg border border-border bg-surface px-4 py-3">
              <p className="font-mono text-lg font-medium text-foreground">
                0 * * * *
              </p>
              <p className="mt-1 text-sm text-muted-foreground">
                Polls hourly; sends once a day at 12:00 PM America/Chicago
              </p>
            </div>
            <a
              href="https://crontab.guru/#0_*_*_*_*"
              target="_blank"
              rel="noopener noreferrer"
              className="mt-3 inline-flex self-start items-center gap-1.5 text-xs font-medium text-primary hover:underline"
            >
              View on crontab.guru
              <ExternalLink className="h-3 w-3" />
            </a>
            <p className="mt-auto pt-4 text-xs text-subtle-foreground">
              The hour is not fixed in UTC: a tick before noon local waits for
              it, so the digest stays at noon across the CDT/CST switch.
            </p>
          </CardContent>
        </Card>

        {/* Telegram */}
        <Card interactive className="flex flex-col">
          <CardHeader className="min-h-[5.5rem] flex-row items-center gap-3 space-y-0">
            <CardIcon icon={Send} />
            <div className="min-w-0">
              <CardTitle>Telegram</CardTitle>
              <CardDescription>Message delivery</CardDescription>
            </div>
          </CardHeader>
          <CardContent className="flex flex-1 flex-col">
            <div className="flex items-center justify-between gap-4 border-b border-border py-2.5">
              <span className="text-sm text-muted-foreground">Status</span>
              <Badge variant="success">Enabled</Badge>
            </div>
            <div className="pt-2.5">
              <p className="text-sm text-muted-foreground">Format</p>
              <p className="mt-1 text-sm font-medium text-foreground">
                Structured dev summary — Why / What / How / Take
              </p>
            </div>
          </CardContent>
        </Card>

        {/* GitHub Actions */}
        <Card interactive className="flex flex-col md:col-span-2 xl:col-span-3">
          <CardHeader className="min-h-[5.5rem] flex-row items-center gap-3 space-y-0">
            <CardIcon icon={GithubIcon} />
            <div className="min-w-0">
              <CardTitle>GitHub Actions</CardTitle>
              <CardDescription>Workflow automation</CardDescription>
            </div>
          </CardHeader>
          <CardContent className="grid flex-1 gap-4 sm:grid-cols-2">
            <div>
              <p className="eyebrow">Workflow</p>
              <code className="mt-2 block font-mono text-sm text-foreground">
                .github/workflows/daily-news.yml
              </code>
            </div>
            <div>
              <p className="eyebrow">Repository</p>
              <a
                href="https://github.com/vickey-kapoor/Applied-AI-Dev-Digest"
                target="_blank"
                rel="noopener noreferrer"
                className="mt-2 inline-flex items-center gap-1.5 font-mono text-sm text-primary hover:underline"
              >
                vickey-kapoor/Applied-AI-Dev-Digest
                <ExternalLink className="h-3.5 w-3.5" />
              </a>
            </div>
          </CardContent>
        </Card>
      </div>

      {/* KV info banner */}
      <Card elevation="flat" className="mt-6 border-primary/20 bg-primary/5">
        <CardContent className="flex items-start gap-3.5 p-5">
          <Info
            className="mt-0.5 h-5 w-5 shrink-0 text-primary"
            aria-hidden="true"
          />
          <div>
            <p className="text-sm font-semibold text-foreground">KV storage</p>
            <p className="mt-1.5 text-sm leading-relaxed text-muted-foreground">
              Topics, pause state and stats are stored in Vercel KV (Upstash
              Redis). Set{" "}
              <code className="rounded bg-primary/10 px-1.5 py-0.5 font-mono text-xs text-foreground">
                KV_REST_API_URL
              </code>{" "}
              and{" "}
              <code className="rounded bg-primary/10 px-1.5 py-0.5 font-mono text-xs text-foreground">
                KV_REST_API_TOKEN
              </code>{" "}
              in both Vercel and GitHub Secrets.
            </p>
          </div>
        </CardContent>
      </Card>
    </div>
  );
}
