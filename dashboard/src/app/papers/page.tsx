import { getPapers } from "@/lib/data";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { ExternalLink, Filter, Star, BookOpen, CheckCircle } from "lucide-react";

export const dynamic = 'force-dynamic';

export default async function PapersPage({
  searchParams,
}: {
  searchParams: { source?: string; topic?: string; status?: string };
}) {
  const papers = await getPapers();

  // Filter papers based on search params
  let filteredPapers = papers;
  const { source, topic, status } = searchParams;
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
        <h1 className="text-2xl font-bold text-gray-900">Research Papers</h1>
        <p className="text-gray-500 mt-1">
          Browse and filter all fetched research papers
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
              <div className="flex flex-wrap gap-2">
                <a
                  href="/papers"
                  className={`px-3 py-1 rounded-full text-sm ${
                    !searchParams.source
                      ? "bg-blue-600 text-white"
                      : "bg-gray-100 text-gray-700 hover:bg-gray-200"
                  }`}
                >
                  All
                </a>
                {sources.map((source) => (
                  <a
                    key={source}
                    href={`/papers?source=${encodeURIComponent(source)}`}
                    className={`px-3 py-1 rounded-full text-sm ${
                      searchParams.source === source
                        ? "bg-blue-600 text-white"
                        : "bg-gray-100 text-gray-700 hover:bg-gray-200"
                    }`}
                  >
                    {source}
                  </a>
                ))}
              </div>
            </div>

            {/* Topic Filter */}
            <div>
              <label className="text-sm text-gray-500 block mb-2">Topic</label>
              <div className="flex flex-wrap gap-2">
                <a
                  href="/papers"
                  className={`px-3 py-1 rounded-full text-sm ${
                    !searchParams.topic
                      ? "bg-blue-600 text-white"
                      : "bg-gray-100 text-gray-700 hover:bg-gray-200"
                  }`}
                >
                  All
                </a>
                {topics.map((topic) => (
                  <a
                    key={topic}
                    href={`/papers?topic=${encodeURIComponent(topic)}`}
                    className={`px-3 py-1 rounded-full text-sm ${
                      searchParams.topic === topic
                        ? "bg-blue-600 text-white"
                        : "bg-gray-100 text-gray-700 hover:bg-gray-200"
                    }`}
                  >
                    {topic}
                  </a>
                ))}
              </div>
            </div>

            {/* Status Filter */}
            <div>
              <label className="text-sm text-gray-500 block mb-2">Status</label>
              <div className="flex flex-wrap gap-2">
                <a
                  href="/papers"
                  className={`px-3 py-1 rounded-full text-sm ${
                    !searchParams.status
                      ? "bg-blue-600 text-white"
                      : "bg-gray-100 text-gray-700 hover:bg-gray-200"
                  }`}
                >
                  All
                </a>
                {['unread', 'read', 'starred'].map((status) => (
                  <a
                    key={status}
                    href={`/papers?status=${status}`}
                    className={`px-3 py-1 rounded-full text-sm capitalize ${
                      searchParams.status === status
                        ? "bg-blue-600 text-white"
                        : "bg-gray-100 text-gray-700 hover:bg-gray-200"
                    }`}
                  >
                    {status}
                  </a>
                ))}
              </div>
            </div>
          </div>
        </CardContent>
      </Card>

      {/* Papers Count */}
      <div className="mb-4 text-sm text-gray-500">
        Showing {filteredPapers.length} of {papers.length} papers
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
                      {paper.ranking_score && (
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
              <p className="text-gray-500">
                {papers.length === 0
                  ? "No papers fetched yet. Run the daily workflow to get started."
                  : "No papers match the selected filters."}
              </p>
            </CardContent>
          </Card>
        )}
      </div>
    </div>
  );
}
