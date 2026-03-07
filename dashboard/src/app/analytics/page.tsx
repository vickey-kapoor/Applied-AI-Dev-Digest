import { getPapers, getDigests } from "@/lib/data";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { BarChart3, TrendingUp, PieChart, Calendar } from "lucide-react";
import { SourceChart } from "@/components/charts/source-chart";
import { TrendsChart } from "@/components/charts/trends-chart";
import { TopicsChart } from "@/components/charts/topics-chart";

export const dynamic = 'force-dynamic';

export default async function AnalyticsPage() {
  const papers = await getPapers();
  const digests = await getDigests();

  // Calculate source distribution
  const sourceCounts = papers.reduce((acc, p) => {
    acc[p.source] = (acc[p.source] || 0) + 1;
    return acc;
  }, {} as Record<string, number>);

  const sourceData = Object.entries(sourceCounts).map(([name, value]) => ({
    name,
    value,
  }));

  // Calculate topic frequency
  const topicCounts = papers.flatMap(p => p.topics).reduce((acc, topic) => {
    acc[topic] = (acc[topic] || 0) + 1;
    return acc;
  }, {} as Record<string, number>);

  const topTopics = Object.entries(topicCounts)
    .sort((a, b) => b[1] - a[1])
    .slice(0, 10)
    .map(([name, count]) => ({ name, count }));

  // Calculate daily trends (last 14 days)
  const dailyCounts: Record<string, number> = {};
  papers.forEach(p => {
    const date = p.fetched_at.split('T')[0];
    dailyCounts[date] = (dailyCounts[date] || 0) + 1;
  });

  const trendsData = Object.entries(dailyCounts)
    .sort((a, b) => a[0].localeCompare(b[0]))
    .slice(-14)
    .map(([date, papers]) => ({
      date: date.slice(5), // MM-DD format
      papers,
    }));

  // Calculate average ranking score
  const avgScore = papers.length > 0
    ? papers.reduce((acc, p) => acc + (p.ranking_score || 0), 0) / papers.length
    : 0;

  // Success rate of WhatsApp sends
  const sentDigests = digests.filter(d => d.whatsapp_sent).length;
  const successRate = digests.length > 0
    ? Math.round((sentDigests / digests.length) * 100)
    : 0;

  return (
    <div className="p-8">
      {/* Header */}
      <div className="mb-8">
        <h1 className="text-2xl font-bold text-gray-900">Analytics</h1>
        <p className="text-gray-500 mt-1">
          Insights and trends from your research digest
        </p>
      </div>

      {/* Summary Stats */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-4 mb-8">
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-medium text-gray-500">
              Total Papers
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{papers.length}</div>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-medium text-gray-500">
              Total Digests
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{digests.length}</div>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-medium text-gray-500">
              Avg. Ranking Score
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{avgScore.toFixed(1)}/10</div>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-medium text-gray-500">
              WhatsApp Success
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{successRate}%</div>
          </CardContent>
        </Card>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Papers by Source */}
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <PieChart className="h-5 w-5 text-blue-600" />
              Papers by Source
            </CardTitle>
          </CardHeader>
          <CardContent>
            {sourceData.length > 0 ? (
              <SourceChart data={sourceData} />
            ) : (
              <div className="h-64 flex items-center justify-center text-gray-500">
                No data available
              </div>
            )}
          </CardContent>
        </Card>

        {/* Daily Trends */}
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <TrendingUp className="h-5 w-5 text-green-600" />
              Daily Paper Count
            </CardTitle>
          </CardHeader>
          <CardContent>
            {trendsData.length > 0 ? (
              <TrendsChart data={trendsData} />
            ) : (
              <div className="h-64 flex items-center justify-center text-gray-500">
                No data available
              </div>
            )}
          </CardContent>
        </Card>

        {/* Top Topics */}
        <Card className="lg:col-span-2">
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <BarChart3 className="h-5 w-5 text-purple-600" />
              Top Research Topics
            </CardTitle>
          </CardHeader>
          <CardContent>
            {topTopics.length > 0 ? (
              <TopicsChart data={topTopics} />
            ) : (
              <div className="h-64 flex items-center justify-center text-gray-500">
                No data available
              </div>
            )}
          </CardContent>
        </Card>
      </div>

      {/* Digest History */}
      <Card className="mt-6">
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <Calendar className="h-5 w-5 text-orange-600" />
            Recent Digest History
          </CardTitle>
        </CardHeader>
        <CardContent>
          {digests.length > 0 ? (
            <div className="overflow-x-auto">
              <table className="w-full text-sm">
                <thead>
                  <tr className="border-b border-gray-200">
                    <th className="text-left py-3 px-4 font-medium text-gray-500">Date</th>
                    <th className="text-left py-3 px-4 font-medium text-gray-500">Papers</th>
                    <th className="text-left py-3 px-4 font-medium text-gray-500">WhatsApp</th>
                    <th className="text-left py-3 px-4 font-medium text-gray-500">PDF</th>
                  </tr>
                </thead>
                <tbody>
                  {digests.slice(0, 10).map((digest) => (
                    <tr key={digest.date} className="border-b border-gray-100">
                      <td className="py-3 px-4 font-medium">{digest.date}</td>
                      <td className="py-3 px-4">{digest.papers_fetched}</td>
                      <td className="py-3 px-4">
                        <span className={`inline-flex px-2 py-1 rounded-full text-xs ${
                          digest.whatsapp_sent
                            ? 'bg-green-100 text-green-700'
                            : 'bg-gray-100 text-gray-600'
                        }`}>
                          {digest.whatsapp_sent ? 'Sent' : 'Not Sent'}
                        </span>
                      </td>
                      <td className="py-3 px-4">
                        {digest.pdf_path ? (
                          <span className="text-blue-600">Available</span>
                        ) : (
                          <span className="text-gray-400">-</span>
                        )}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          ) : (
            <div className="py-8 text-center text-gray-500">
              No digest history yet. Run the daily workflow to generate digests.
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  );
}
