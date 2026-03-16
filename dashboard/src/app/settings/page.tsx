import { getConfig } from "@/lib/data";
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import {
  Settings as SettingsIcon,
  Search,
  Database,
  Clock,
  Send,
  Github,
  ExternalLink,
} from "lucide-react";

export default function SettingsPage() {
  const config = getConfig();

  return (
    <div className="p-8">
      {/* Header */}
      <div className="mb-8">
        <h1 className="text-2xl font-bold text-gray-900">Settings</h1>
        <p className="text-gray-500 mt-1">
          View and manage your dev digest configuration
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
              Keywords used to filter developer product updates
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
              Edit keywords in src/constants.py
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
              AI lab blogs being monitored for product updates
            </CardDescription>
          </CardHeader>
          <CardContent>
            <div className="space-y-3">
              <div className="flex items-center justify-between py-2 border-b border-gray-100">
                <span className="font-medium">AI Lab Blogs</span>
                <Badge variant={config.sources.blogs ? "success" : "secondary"}>
                  {config.sources.blogs ? "Enabled" : "Disabled"}
                </Badge>
              </div>
            </div>
            <div className="mt-4">
              <p className="text-sm text-gray-500 mb-2">Tracked Labs</p>
              <div className="flex flex-wrap gap-2">
                {config.labs.map((lab) => (
                  <Badge key={lab} variant="secondary" className="text-sm">
                    {lab}
                  </Badge>
                ))}
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
              When the dev digest runs
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

        {/* Telegram */}
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <Send className="h-5 w-5 text-blue-500" />
              Telegram Notifications
            </CardTitle>
            <CardDescription>
              Message delivery settings
            </CardDescription>
          </CardHeader>
          <CardContent>
            <div className="space-y-4">
              <div className="flex items-center justify-between">
                <span className="font-medium">Status</span>
                <Badge variant={config.telegram_enabled ? "success" : "secondary"}>
                  {config.telegram_enabled ? "Enabled" : "Disabled"}
                </Badge>
              </div>
              <div>
                <p className="text-sm text-gray-500">Provider</p>
                <p className="font-medium">Telegram Bot API</p>
              </div>
              <div>
                <p className="text-sm text-gray-500">Message Format</p>
                <p className="font-medium">Developer Summary with Markdown</p>
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
                  href="https://github.com/vickey-kapoor/ai-research-digest"
                  target="_blank"
                  rel="noopener noreferrer"
                  className="text-blue-600 hover:underline inline-flex items-center gap-1"
                >
                  vickey-kapoor/ai-research-digest
                  <ExternalLink className="h-4 w-4" />
                </a>
              </div>
              <div className="md:col-span-2">
                <p className="text-sm text-gray-500 mb-2">Manual Trigger</p>
                <a
                  href="https://github.com/vickey-kapoor/ai-research-digest/actions/workflows/daily-news.yml"
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
            <p className="font-medium text-blue-900">Configuration</p>
            <p className="text-sm text-blue-700 mt-1">
              Settings are defined in <code className="bg-blue-100 px-1 rounded">src/constants.py</code>.
              Changes take effect on the next workflow run.
            </p>
          </div>
        </div>
      </div>
    </div>
  );
}
