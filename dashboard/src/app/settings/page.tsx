import { getConfig } from "@/lib/data";
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import {
  Settings as SettingsIcon,
  Search,
  Database,
  Clock,
  MessageSquare,
  Github,
  ExternalLink,
} from "lucide-react";

export const dynamic = 'force-dynamic';

export default async function SettingsPage() {
  const config = await getConfig();

  return (
    <div className="p-8">
      {/* Header */}
      <div className="mb-8">
        <h1 className="text-2xl font-bold text-gray-900">Settings</h1>
        <p className="text-gray-500 mt-1">
          View and manage your research digest configuration
        </p>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Keywords */}
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <Search className="h-5 w-5 text-blue-600" />
              Search Keywords
            </CardTitle>
            <CardDescription>
              Keywords used to filter AI research papers
            </CardDescription>
          </CardHeader>
          <CardContent>
            <div className="flex flex-wrap gap-2">
              {config.keywords.map((keyword) => (
                <Badge key={keyword} variant="secondary" className="text-sm">
                  {keyword}
                </Badge>
              ))}
            </div>
            <p className="text-xs text-gray-400 mt-4">
              Edit keywords in data/config.json
            </p>
          </CardContent>
        </Card>

        {/* Data Sources */}
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <Database className="h-5 w-5 text-green-600" />
              Data Sources
            </CardTitle>
            <CardDescription>
              Research paper sources being monitored
            </CardDescription>
          </CardHeader>
          <CardContent>
            <div className="space-y-3">
              <div className="flex items-center justify-between py-2 border-b border-gray-100">
                <span className="font-medium">arXiv</span>
                <Badge variant={config.sources.arxiv ? "success" : "secondary"}>
                  {config.sources.arxiv ? "Enabled" : "Disabled"}
                </Badge>
              </div>
              <div className="flex items-center justify-between py-2 border-b border-gray-100">
                <span className="font-medium">Hugging Face Daily Papers</span>
                <Badge variant={config.sources.huggingface ? "success" : "secondary"}>
                  {config.sources.huggingface ? "Enabled" : "Disabled"}
                </Badge>
              </div>
              <div className="flex items-center justify-between py-2 border-b border-gray-100">
                <span className="font-medium">Papers With Code</span>
                <Badge variant={config.sources.pwc ? "success" : "secondary"}>
                  {config.sources.pwc ? "Enabled" : "Disabled"}
                </Badge>
              </div>
              <div className="flex items-center justify-between py-2">
                <span className="font-medium">AI Lab Blogs</span>
                <Badge variant={config.sources.blogs ? "success" : "secondary"}>
                  {config.sources.blogs ? "Enabled" : "Disabled"}
                </Badge>
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
            <CardDescription>
              When the research digest runs
            </CardDescription>
          </CardHeader>
          <CardContent>
            <div className="space-y-4">
              <div>
                <p className="text-sm text-gray-500">Cron Expression</p>
                <p className="font-mono text-lg">{config.schedule}</p>
              </div>
              <div>
                <p className="text-sm text-gray-500">Human Readable</p>
                <p className="font-medium">Daily at 10:00 AM CST (16:00 UTC)</p>
              </div>
              <div className="pt-2">
                <a
                  href="https://crontab.guru/#0_16_*_*_*"
                  target="_blank"
                  rel="noopener noreferrer"
                  className="text-sm text-blue-600 hover:underline inline-flex items-center gap-1"
                >
                  View on crontab.guru
                  <ExternalLink className="h-3 w-3" />
                </a>
              </div>
            </div>
          </CardContent>
        </Card>

        {/* WhatsApp */}
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <MessageSquare className="h-5 w-5 text-green-600" />
              WhatsApp Notifications
            </CardTitle>
            <CardDescription>
              Message delivery settings
            </CardDescription>
          </CardHeader>
          <CardContent>
            <div className="space-y-4">
              <div className="flex items-center justify-between">
                <span className="font-medium">Status</span>
                <Badge variant={config.whatsapp_enabled ? "success" : "secondary"}>
                  {config.whatsapp_enabled ? "Enabled" : "Disabled"}
                </Badge>
              </div>
              <div>
                <p className="text-sm text-gray-500">Provider</p>
                <p className="font-medium">Twilio WhatsApp API</p>
              </div>
              <div>
                <p className="text-sm text-gray-500">Message Format</p>
                <p className="font-medium">ELI5 Summary (max 1600 chars)</p>
              </div>
            </div>
          </CardContent>
        </Card>

        {/* GitHub Actions */}
        <Card className="lg:col-span-2">
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <Github className="h-5 w-5 text-gray-900" />
              GitHub Actions
            </CardTitle>
            <CardDescription>
              Workflow automation controls
            </CardDescription>
          </CardHeader>
          <CardContent>
            <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
              <div>
                <p className="text-sm text-gray-500 mb-2">Workflow File</p>
                <code className="text-sm bg-gray-100 px-3 py-2 rounded-lg block">
                  .github/workflows/daily-news.yml
                </code>
              </div>
              <div>
                <p className="text-sm text-gray-500 mb-2">Repository</p>
                <a
                  href="https://github.com/vickey-kapoor/ai-research-whatsapp-digest"
                  target="_blank"
                  rel="noopener noreferrer"
                  className="text-blue-600 hover:underline inline-flex items-center gap-1"
                >
                  vickey-kapoor/ai-research-whatsapp-digest
                  <ExternalLink className="h-4 w-4" />
                </a>
              </div>
              <div className="md:col-span-2">
                <p className="text-sm text-gray-500 mb-2">Manual Trigger</p>
                <a
                  href="https://github.com/vickey-kapoor/ai-research-whatsapp-digest/actions/workflows/daily-news.yml"
                  target="_blank"
                  rel="noopener noreferrer"
                  className="inline-flex items-center gap-2 px-4 py-2 bg-gray-900 text-white rounded-lg hover:bg-gray-800 transition-colors"
                >
                  <Github className="h-4 w-4" />
                  Run Workflow on GitHub
                </a>
              </div>
            </div>
          </CardContent>
        </Card>
      </div>

      {/* Info Banner */}
      <div className="mt-8 p-4 bg-blue-50 rounded-lg border border-blue-100">
        <div className="flex items-start gap-3">
          <SettingsIcon className="h-5 w-5 text-blue-600 mt-0.5" />
          <div>
            <p className="font-medium text-blue-900">Configuration Files</p>
            <p className="text-sm text-blue-700 mt-1">
              Settings are stored in <code className="bg-blue-100 px-1 rounded">data/config.json</code>.
              Edit this file directly or update via GitHub to change configuration.
              Changes take effect on the next workflow run.
            </p>
          </div>
        </div>
      </div>
    </div>
  );
}
