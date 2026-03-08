import { getStats, getPapers, getDigests } from "@/lib/data";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import {
  FileText,
  Send,
  TrendingUp,
  Clock,
  Star,
  BookOpen,
  ExternalLink,
} from "lucide-react";
import Link from "next/link";

export default function DashboardPage() {
  const stats = getStats();
  const papers = getPapers();
  const digests = getDigests();

  // Debug: Log at render time
  console.log('[PAGE] DashboardPage render - papers:', papers.length, 'digests:', digests.length);

  // Get latest digest
  const latestDigest = digests[0];

  // Get top paper
  const topPaper = papers.find(p => p.id === latestDigest?.top_paper_id) || papers[0];

  // Recent papers (last 5)
  const recentPapers = papers.slice(0, 5);

  return (
    <div className="p-8">
      {/* Debug Banner - Remove after fixing */}
      <div className="mb-4 p-3 bg-yellow-100 border border-yellow-400 rounded text-sm">
        <strong>Debug:</strong> papers.length={papers.length}, digests.length={digests.length}, stats.totalPapers={stats.totalPapers}
      </div>

      {/* Header */}
      <div className="mb-8">
        <h1 className="text-2xl font-bold text-gray-900">Dashboard</h1>
        <p className="text-gray-500 mt-1">
          Your AI research digest overview
        </p>
      </div>

      {/* Stats Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4 mb-8">
        <Card>
          <CardHeader className="flex flex-row items-center justify-between pb-2">
            <CardTitle className="text-sm font-medium text-gray-500">
              Total Papers
            </CardTitle>
            <FileText className="h-4 w-4 text-gray-400" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{stats.totalPapers}</div>
            <p className="text-xs text-gray-500 mt-1">
              {stats.todaysPapers} fetched today
            </p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="flex flex-row items-center justify-between pb-2">
            <CardTitle className="text-sm font-medium text-gray-500">
              Digests Sent
            </CardTitle>
            <Send className="h-4 w-4 text-gray-400" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{stats.totalDigests}</div>
            <p className="text-xs text-gray-500 mt-1">
              {latestDigest?.whatsapp_sent ? "Latest sent" : "Pending"}
            </p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="flex flex-row items-center justify-between pb-2">
            <CardTitle className="text-sm font-medium text-gray-500">
              Unread
            </CardTitle>
            <BookOpen className="h-4 w-4 text-gray-400" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{stats.unreadCount}</div>
            <p className="text-xs text-gray-500 mt-1">
              Papers to review
            </p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="flex flex-row items-center justify-between pb-2">
            <CardTitle className="text-sm font-medium text-gray-500">
              Starred
            </CardTitle>
            <Star className="h-4 w-4 text-gray-400" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{stats.starredCount}</div>
            <p className="text-xs text-gray-500 mt-1">
              Important papers
            </p>
          </CardContent>
        </Card>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
        {/* Top Paper Today */}
        <div className="lg:col-span-2">
          <Card>
            <CardHeader>
              <div className="flex items-center justify-between">
                <CardTitle className="flex items-center gap-2">
                  <TrendingUp className="h-5 w-5 text-blue-600" />
                  Top Paper Today
                </CardTitle>
                {topPaper && (
                  <Badge variant="secondary">{topPaper.source}</Badge>
                )}
              </div>
            </CardHeader>
            <CardContent>
              {topPaper ? (
                <div>
                  <h3 className="font-semibold text-gray-900 mb-2">
                    {topPaper.title}
                  </h3>
                  <p className="text-sm text-gray-600 mb-4 line-clamp-3">
                    {topPaper.description}
                  </p>
                  <div className="flex items-center justify-between">
                    <div className="flex flex-wrap gap-2">
                      {topPaper.topics.slice(0, 3).map((topic) => (
                        <Badge key={topic} variant="outline">
                          {topic}
                        </Badge>
                      ))}
                    </div>
                    <a
                      href={topPaper.url}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="inline-flex items-center gap-1 text-sm text-blue-600 hover:underline"
                    >
                      Read paper
                      <ExternalLink className="h-3 w-3" />
                    </a>
                  </div>
                  {topPaper.ranking_score && (
                    <div className="mt-4 pt-4 border-t border-gray-100">
                      <div className="flex items-center gap-2">
                        <span className="text-sm text-gray-500">Relevance Score:</span>
                        <div className="flex-1 h-2 bg-gray-100 rounded-full overflow-hidden">
                          <div
                            className="h-full bg-blue-600 rounded-full"
                            style={{ width: `${topPaper.ranking_score * 10}%` }}
                          />
                        </div>
                        <span className="text-sm font-medium text-gray-700">
                          {topPaper.ranking_score}/10
                        </span>
                      </div>
                    </div>
                  )}
                </div>
              ) : (
                <p className="text-gray-500">No papers fetched yet. Run the workflow to get started.</p>
              )}
            </CardContent>
          </Card>
        </div>

        {/* Latest Digest */}
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <Clock className="h-5 w-5 text-green-600" />
              Latest Digest
            </CardTitle>
          </CardHeader>
          <CardContent>
            {latestDigest ? (
              <div className="space-y-4">
                <div>
                  <p className="text-sm text-gray-500">Date</p>
                  <p className="font-medium">{latestDigest.date}</p>
                </div>
                <div>
                  <p className="text-sm text-gray-500">Papers Fetched</p>
                  <p className="font-medium">{latestDigest.papers_fetched}</p>
                </div>
                <div>
                  <p className="text-sm text-gray-500">WhatsApp Status</p>
                  <Badge variant={latestDigest.whatsapp_sent ? "success" : "warning"}>
                    {latestDigest.whatsapp_sent ? "Sent" : "Pending"}
                  </Badge>
                </div>
                {latestDigest.pdf_path && (
                  <div>
                    <p className="text-sm text-gray-500 mb-2">PDF Report</p>
                    <Link
                      href={`/reports?date=${latestDigest.date}`}
                      className="text-sm text-blue-600 hover:underline"
                    >
                      View Report
                    </Link>
                  </div>
                )}
              </div>
            ) : (
              <p className="text-gray-500">No digests sent yet.</p>
            )}
          </CardContent>
        </Card>
      </div>

      {/* Recent Papers */}
      <Card className="mt-8">
        <CardHeader>
          <div className="flex items-center justify-between">
            <CardTitle>Recent Papers</CardTitle>
            <Link
              href="/papers"
              className="text-sm text-blue-600 hover:underline"
            >
              View all
            </Link>
          </div>
        </CardHeader>
        <CardContent>
          {recentPapers.length > 0 ? (
            <div className="space-y-4">
              {recentPapers.map((paper) => (
                <div
                  key={paper.id}
                  className="flex items-start justify-between py-3 border-b border-gray-100 last:border-0"
                >
                  <div className="flex-1 min-w-0 pr-4">
                    <h4 className="font-medium text-gray-900 truncate">
                      {paper.title}
                    </h4>
                    <p className="text-sm text-gray-500 truncate">
                      {paper.authors}
                    </p>
                  </div>
                  <div className="flex items-center gap-2 flex-shrink-0">
                    <Badge variant="outline">{paper.source}</Badge>
                    <a
                      href={paper.url}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="text-gray-400 hover:text-blue-600"
                    >
                      <ExternalLink className="h-4 w-4" />
                    </a>
                  </div>
                </div>
              ))}
            </div>
          ) : (
            <p className="text-gray-500 py-4 text-center">
              No papers yet. Run the daily workflow to fetch research papers.
            </p>
          )}
        </CardContent>
      </Card>
    </div>
  );
}
