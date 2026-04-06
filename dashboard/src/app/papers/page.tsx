import { getPapers } from "@/lib/data";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { ExternalLink, Filter, Star, BookOpen, CheckCircle, FileText } from "lucide-react";
import Link from "next/link";
import { SearchInput } from "./search-input";

export default async function PapersPage({
  searchParams,
}: {
  searchParams: Promise<{
    source?: string;
    topic?: string;
    status?: string;
    q?: string;
    page?: string;
    sort?: string;
    dir?: string;
  }>;
}) {
  const papers = await getPapers();
  const params = await searchParams;

  // Filter papers based on search params
  let filteredPapers = papers;
  const { source, topic, status, q, sort, dir } = params;

  if (q) {
    const query = q.toLowerCase();
    filteredPapers = filteredPapers.filter(
      p =>
        p.title.toLowerCase().includes(query) ||
        p.description.toLowerCase().includes(query)
    );
  }
  if (source) {
    filteredPapers = filteredPapers.filter(p => p.source === source);
  }
  if (topic) {
    filteredPapers = filteredPapers.filter(p => p.topics.includes(topic));
  }
  if (status) {
    filteredPapers = filteredPapers.filter(p => p.status === status);
  }

  // Sorting
  const sortField = sort || "date";
  const sortDir = dir === "asc" ? 1 : -1;

  filteredPapers = [...filteredPapers].sort((a, b) => {
    switch (sortField) {
      case "score":
        return ((a.ranking_score || 0) - (b.ranking_score || 0)) * sortDir;
      case "source":
        return a.source.localeCompare(b.source) * sortDir;
      case "date":
      default:
        return (a.published_at || "").localeCompare(b.published_at || "") * sortDir;
    }
  });

  // Default sort: date descending (most recent first)
  if (!sort && !dir) {
    filteredPapers.reverse();
  }

  // Pagination
  const pageSize = 20;
  const currentPage = Math.max(1, parseInt(params.page || "1", 10) || 1);
  const totalPages = Math.max(1, Math.ceil(filteredPapers.length / pageSize));
  const safePage = Math.min(currentPage, totalPages);
  const paginatedPapers = filteredPapers.slice(
    (safePage - 1) * pageSize,
    safePage * pageSize
  );

  // Get unique sources and topics for filters
  const sources = [...new Set(papers.map(p => p.source))];
  const topics = [...new Set(papers.flatMap(p => p.topics))].slice(0, 10);

  const getStatusIcon = (paperStatus: string) => {
    switch (paperStatus) {
      case "starred":
        return <Star className="h-4 w-4 text-yellow-500 fill-yellow-500" />;
      case "read":
        return <CheckCircle className="h-4 w-4 text-green-500" />;
      default:
        return <BookOpen className="h-4 w-4 text-gray-400" />;
    }
  };

  // Build URL with current params preserved
  function buildUrl(overrides: Record<string, string | undefined>) {
    const p = new URLSearchParams();
    const merged = { source, topic, status, q, sort, dir, page: undefined as string | undefined, ...overrides };
    for (const [k, v] of Object.entries(merged)) {
      if (v) p.set(k, v);
    }
    const qs = p.toString();
    return `/papers${qs ? `?${qs}` : ""}`;
  }

  const nextSortDir = dir === "asc" ? "desc" : "asc";

  return (
    <div className="p-8">
      {/* Header */}
      <div className="mb-8">
        <h1 className="text-2xl font-bold text-gray-900 dark:text-gray-100">Product Updates</h1>
        <p className="text-gray-500 mt-1">
          Browse and filter developer product updates from AI labs
        </p>
      </div>

      {/* Search */}
      <SearchInput defaultValue={q || ""} />

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
                  href={buildUrl({ source: undefined })}
                  className={`px-3 py-1 rounded-full text-sm ${
                    !source ? "bg-blue-600 text-white" : "bg-gray-100 text-gray-700 hover:bg-gray-200 dark:bg-gray-800 dark:text-gray-300 dark:hover:bg-gray-700"
                  }`}
                  role="button"
                >
                  All
                </Link>
                {sources.map((s) => (
                  <Link
                    key={s}
                    href={buildUrl({ source: s, page: undefined })}
                    className={`px-3 py-1 rounded-full text-sm ${
                      source === s ? "bg-blue-600 text-white" : "bg-gray-100 text-gray-700 hover:bg-gray-200 dark:bg-gray-800 dark:text-gray-300 dark:hover:bg-gray-700"
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
                  href={buildUrl({ topic: undefined })}
                  className={`px-3 py-1 rounded-full text-sm ${
                    !topic ? "bg-blue-600 text-white" : "bg-gray-100 text-gray-700 hover:bg-gray-200 dark:bg-gray-800 dark:text-gray-300 dark:hover:bg-gray-700"
                  }`}
                  role="button"
                >
                  All
                </Link>
                {topics.map((t) => (
                  <Link
                    key={t}
                    href={buildUrl({ topic: t, page: undefined })}
                    className={`px-3 py-1 rounded-full text-sm ${
                      topic === t ? "bg-blue-600 text-white" : "bg-gray-100 text-gray-700 hover:bg-gray-200 dark:bg-gray-800 dark:text-gray-300 dark:hover:bg-gray-700"
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
                  href={buildUrl({ status: undefined })}
                  className={`px-3 py-1 rounded-full text-sm ${
                    !status ? "bg-blue-600 text-white" : "bg-gray-100 text-gray-700 hover:bg-gray-200 dark:bg-gray-800 dark:text-gray-300 dark:hover:bg-gray-700"
                  }`}
                  role="button"
                >
                  All
                </Link>
                {(["unread", "read", "starred"] as const).map((s) => (
                  <Link
                    key={s}
                    href={buildUrl({ status: s, page: undefined })}
                    className={`px-3 py-1 rounded-full text-sm capitalize ${
                      status === s ? "bg-blue-600 text-white" : "bg-gray-100 text-gray-700 hover:bg-gray-200 dark:bg-gray-800 dark:text-gray-300 dark:hover:bg-gray-700"
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

      {/* Sort & Count */}
      <div className="flex items-center justify-between mb-4">
        <div className="text-sm text-gray-500">
          Showing {paginatedPapers.length} of {filteredPapers.length} updates
          {filteredPapers.length !== papers.length && ` (${papers.length} total)`}
        </div>
        <div className="flex items-center gap-2 text-sm">
          <span className="text-gray-500">Sort:</span>
          {[
            { key: "date", label: "Date" },
            { key: "score", label: "Score" },
            { key: "source", label: "Source" },
          ].map(({ key, label }) => (
            <Link
              key={key}
              href={buildUrl({
                sort: key,
                dir: sort === key ? nextSortDir : "desc",
                page: undefined,
              })}
              className={`px-2 py-1 rounded text-sm ${
                (sort || "date") === key
                  ? "bg-blue-100 dark:bg-blue-900/30 text-blue-700 dark:text-blue-400 font-medium"
                  : "text-gray-600 dark:text-gray-400 hover:bg-gray-100 dark:hover:bg-gray-800"
              }`}
            >
              {label}
              {(sort || "date") === key && (
                <span className="ml-1">{dir === "asc" ? "\u2191" : "\u2193"}</span>
              )}
            </Link>
          ))}
        </div>
      </div>

      {/* Papers List */}
      <div className="space-y-4">
        {paginatedPapers.length > 0 ? (
          paginatedPapers.map((paper) => (
            <Link key={paper.id} href={`/papers/${paper.id}`} className="block">
              <Card className="hover:shadow-md transition-shadow">
                <CardContent className="p-6">
                  <div className="flex items-start justify-between gap-4">
                    <div className="flex-1 min-w-0">
                      <div className="flex items-center gap-2 mb-2">
                        {getStatusIcon(paper.status)}
                        <h3 className="font-semibold text-gray-900 dark:text-gray-100">
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
                        {paper.topics.slice(0, 3).map((t) => (
                          <Badge key={t} variant="outline">
                            {t}
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
                      className="flex-shrink-0 p-2 rounded-lg bg-gray-50 dark:bg-gray-800 hover:bg-blue-50 dark:hover:bg-blue-900/30 text-gray-500 hover:text-blue-600 transition-colors"
                      aria-label={`Open ${paper.title} in new tab`}
                    >
                      <ExternalLink className="h-5 w-5" />
                    </a>
                  </div>
                </CardContent>
              </Card>
            </Link>
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
                  : "Try adjusting your filters or search query."}
              </p>
            </CardContent>
          </Card>
        )}
      </div>

      {/* Pagination */}
      {totalPages > 1 && (
        <div className="flex items-center justify-center gap-4 mt-8">
          {safePage > 1 ? (
            <Link
              href={buildUrl({ page: String(safePage - 1) })}
              className="px-4 py-2 bg-white dark:bg-gray-800 border border-gray-200 dark:border-gray-700 rounded-lg text-sm hover:bg-gray-50 dark:hover:bg-gray-700"
            >
              Previous
            </Link>
          ) : (
            <button disabled className="px-4 py-2 bg-gray-50 dark:bg-gray-800 border border-gray-100 dark:border-gray-700 rounded-lg text-sm text-gray-400 cursor-not-allowed">
              Previous
            </button>
          )}
          <span className="text-sm text-gray-600">
            Page {safePage} of {totalPages}
          </span>
          {safePage < totalPages ? (
            <Link
              href={buildUrl({ page: String(safePage + 1) })}
              className="px-4 py-2 bg-white dark:bg-gray-800 border border-gray-200 dark:border-gray-700 rounded-lg text-sm hover:bg-gray-50 dark:hover:bg-gray-700"
            >
              Next
            </Link>
          ) : (
            <button disabled className="px-4 py-2 bg-gray-50 dark:bg-gray-800 border border-gray-100 dark:border-gray-700 rounded-lg text-sm text-gray-400 cursor-not-allowed">
              Next
            </button>
          )}
        </div>
      )}
    </div>
  );
}
