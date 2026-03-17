import { getPapers } from "@/lib/data";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import {
  ArrowLeft,
  ExternalLink,
  Star,
  BookOpen,
  CheckCircle,
  Calendar,
  User,
} from "lucide-react";
import Link from "next/link";
import { notFound } from "next/navigation";

export default async function PaperDetailPage({
  params,
}: {
  params: Promise<{ id: string }>;
}) {
  const { id } = await params;
  const papers = await getPapers();
  const paper = papers.find((p) => p.id === id);

  if (!paper) {
    notFound();
  }

  const statusDisplay = {
    starred: {
      icon: <Star className="h-5 w-5 text-yellow-500 fill-yellow-500" />,
      label: "Starred",
      variant: "warning" as const,
    },
    read: {
      icon: <CheckCircle className="h-5 w-5 text-green-500" />,
      label: "Read",
      variant: "success" as const,
    },
    unread: {
      icon: <BookOpen className="h-5 w-5 text-gray-400" />,
      label: "Unread",
      variant: "secondary" as const,
    },
  };

  const st = statusDisplay[paper.status] || statusDisplay.unread;

  return (
    <div className="p-8 max-w-4xl mx-auto">
      {/* Back navigation */}
      <Link
        href="/papers"
        className="inline-flex items-center gap-2 text-sm text-gray-600 hover:text-blue-600 mb-6"
      >
        <ArrowLeft className="h-4 w-4" />
        Back to updates
      </Link>

      {/* Header Card */}
      <Card className="mb-6">
        <CardHeader>
          <div className="flex items-start justify-between gap-4">
            <div className="flex-1">
              <div className="flex items-center gap-2 mb-3">
                {st.icon}
                <Badge variant={st.variant}>{st.label}</Badge>
                <Badge variant="secondary">{paper.source}</Badge>
              </div>
              <CardTitle className="text-xl leading-tight">
                {paper.title}
              </CardTitle>
            </div>
            <a
              href={paper.url}
              target="_blank"
              rel="noopener noreferrer"
              className="flex-shrink-0 px-4 py-2 bg-blue-600 text-white text-sm rounded-lg hover:bg-blue-700 inline-flex items-center gap-2"
              aria-label="Open original article"
            >
              Open
              <ExternalLink className="h-4 w-4" />
            </a>
          </div>
        </CardHeader>
        <CardContent>
          <div className="flex flex-wrap items-center gap-4 text-sm text-gray-500 mb-4">
            <span className="inline-flex items-center gap-1">
              <User className="h-4 w-4" />
              {paper.authors}
            </span>
            <span className="inline-flex items-center gap-1">
              <Calendar className="h-4 w-4" />
              {paper.published_at}
            </span>
            {paper.ranking_score > 0 && (
              <Badge variant="default">Score: {paper.ranking_score}/10</Badge>
            )}
          </div>
          <div className="flex flex-wrap gap-2">
            {paper.topics.map((topic) => (
              <Badge key={topic} variant="outline">
                {topic}
              </Badge>
            ))}
          </div>
        </CardContent>
      </Card>

      {/* Description */}
      <Card>
        <CardHeader>
          <CardTitle className="text-base">Description</CardTitle>
        </CardHeader>
        <CardContent>
          <p className="text-gray-700 leading-relaxed whitespace-pre-line">
            {paper.description || "No description available."}
          </p>
        </CardContent>
      </Card>
    </div>
  );
}
