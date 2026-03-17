import { getPapers } from "@/lib/data";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { ExternalLink, Filter, Star, BookOpen, CheckCircle, FileText } from "lucide-react";
import Link from "next/link";

export default async function PapersPage({
  searchParams,
}: {
  searchParams: Promise<{ source?: string; topic?: string; status?: string }>;
}) {
  const papers = await getPapers();
  const params = await searchParams;

  // Filter papers based on search params
  let filteredPapers = papers;
  const { source, topic, status } = params;
  if (source) {
    filteredPapers = filteredPapers.filter(p => p.source === source);
  }
  if (topic) {
    filteredPapers = filteredPapers.filter(p => p.topics.includes(topic));
  }
  if (status) {
    filteredPapers = filteredPapers.filter(p => p.status === status);
  }

  // Get unique sources and topics for filters
  const sources = [...new Set(papers.map(p => p.source))];
  const topics = [...new Set(papers.flatMap(p => p.topics))].slice(0, 10);

  const getStatusIcon = (status: string) => {
    switch (status) {
      case 'starred':
        return <Star className="h-4 w-4 text-yellow-500 fill-yellow-500" />;
      case 'read':
        return <CheckCircle className="h-4 w-4 text-green-500" />;
      default:
        return <BookOpen className="h-4 w-4 text-gray-400" />;
    }
  };

  return (
    <div className="p-8">
      {/* Header */}
      <div className="mb-8">
        <h1 className="text-2xl font-bold text-gray-900">Product Updates</h1>
        <p className="text-gray-500 mt-1">
          Browse and filter developer product updates from AI labs
        </p>
      </div>

      {/* Filters */}
      <Card className="mb-6">
        <CardHeader className="pb-3">
          <CardTitle className="text-sm font-medium flex items-center gap-2">
            <Filter className="h-4 w-4" />
            Filters
          </CardTitle>
        </CardHeader>
        <CardContent>
          <div className="flex flex-wrap gap-4">
            {/* Source Filter */}
            <div>
              <label className="text-sm text-gray-500 block mb-2">Source</label>
              <div className="flex flex-wrap gap-2" role="group" aria-label="Filter by source">
                <Link
                  href="/papers"
                  className={`px-3 py-1 rounded-full text-sm ${
                    !params.source
                      ? "bg-blue-600 text-white"
                      : "bg-gray-100 text-gray-700 hover:bg-gray-200"
                  }`}
                  role="button"
                >
                  All
                </Link>
                {sources.map((s) => (
                  <Link
                    key={s}
                    href={`/papers?source=${encodeURIComponent(s)}`}
                    className={`px-3 py-1 rounded-full text-sm ${
                      params.source === s
                        ? "bg-blue-600 text-white"
                        : "bg-gray-100 text-gray-700 hover:bg-gray-200"
                    }`}
                    role="button"
                  >
                    {s}
                  </Link>
                ))}
              </div>
            </div>

            {/* Topic Filter */}
            <div>
              <label className="text-sm text-gray-500 block mb-2">Topic</label>
              <div className="flex flex-wrap gap-2" role="group" aria-label="Filter by topic">
                <Link
                  href="/papers"
                  className={`px-3 py-1 rounded-full text-sm ${
                    !params.topic
                      ? "bg-blue-600 text-white"
                      : "bg-gray-100 text-gray-700 hover:bg-gray-200"
                  }`}
                  role="button"
                >
                  All
                </Link>
                {topics.map((t) => (
                  <Link
                    key={t}
                    href={`/papers?topic=${encodeURIComponent(t)}`}
                    className={`px-3 py-1 rounded-full text-sm ${
                      params.topic === t
                        ? "bg-blue-600 text-white"
                        : "bg-gray-100 text-gray-700 hover:bg-gray-200"
                    }`}
                    role="button"
                  >
                    {t}
                  </Link>
                ))}
              </div>
            </div>

            {/* Status Filter */}
            <div>
              <label className="text-sm text-gray-500 block mb-2">Status</label>
              <div className="flex flex-wrap gap-2" role="group" aria-label="Filter by status">
                <Link
                  href="/papers"
                  className={`px-3 py-1 rounded-full text-sm ${
                    !params.status
                      ? "bg-blue-600 text-white"
                      : "bg-gray-100 text-gray-700 hover:bg-gray-200"
                  }`}
                  role="button"
                >
                  All
                </Link>
                {['unread', 'read', 'starred'].map((s) => (
                  <Link
                    key={s}
                    href={`/papers?status=${s}`}
                    className={`px-3 py-1 rounded-full text-sm capitalize ${
                      params.status === s
                        ? "bg-blue-600 text-white"
                        : "bg-gray-100 text-gray-700 hover:bg-gray-200"
                    }`}
                    role="button"
                  >
                    {s}
                  </Link>
                ))}
              </div>
            </div>
          </div>
        </CardContent>
      </Card>

      {/* Papers Count */}
      <div className="mb-4 text-sm text-gray-500">
        Showing {filteredPapers.length} of {papers.length} updates
      </div>

      {/* Papers List */}
      <div className="space-y-4">
        {filteredPapers.length > 0 ? (
          filteredPapers.map((paper) => (
            <Card key={paper.id} className="hover:shadow-md transition-shadow">
              <CardContent className="p-6">
                <div className="flex items-start justify-between gap-4">
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-2 mb-2">
                      {getStatusIcon(paper.status)}
                      <h3 className="font-semibold text-gray-900">
                        {paper.title}
                      </h3>
                    </div>
                    <p className="text-sm text-gray-600 mb-3 line-clamp-2">
                      {paper.description}
                    </p>
                    <div className="flex flex-wrap items-center gap-2 text-sm text-gray-500">
                      <span>{paper.authors}</span>
                      <span className="text-gray-300">|</span>
                      <span>{paper.published_at}</span>
                    </div>
                    <div className="flex flex-wrap gap-2 mt-3">
                      <Badge variant="secondary">{paper.source}</Badge>
                      {paper.topics.slice(0, 3).map((topic) => (
                        <Badge key={topic} variant="outline">
                          {topic}
                        </Badge>
                      ))}
                      {paper.ranking_score > 0 && (
                        <Badge variant="default">
                          Score: {paper.ranking_score}/10
                        </Badge>
                      )}
                    </div>
                  </div>
                  <a
                    href={paper.url}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="flex-shrink-0 p-2 rounded-lg bg-gray-50 hover:bg-blue-50 text-gray-500 hover:text-blue-600 transition-colors"
                    aria-label={`Open ${paper.title} in new tab`}
                  >
                    <ExternalLink className="h-5 w-5" />
                  </a>
                </div>
              </CardContent>
            </Card>
          ))
        ) : (
          <Card>
            <CardContent className="p-12 text-center">
              <FileText className="h-12 w-12 text-gray-300 mx-auto mb-4" />
              <p className="text-gray-500 text-lg">
                {papers.length === 0
                  ? "No updates fetched yet"
                  : "No updates match the selected filters"}
              </p>
              <p className="text-gray-400 text-sm mt-2">
                {papers.length === 0
                  ? "Run the daily workflow to fetch product updates from AI labs."
                  : "Try adjusting your filters to see more results."}
              </p>
            </CardContent>
          </Card>
        )}
      </div>
    </div>
  );
}
