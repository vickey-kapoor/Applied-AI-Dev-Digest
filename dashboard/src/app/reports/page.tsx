import { getReportDates, getDigests } from "@/lib/data";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Calendar, FileText, ExternalLink } from "lucide-react";
import Link from "next/link";

export const dynamic = 'force-dynamic';

export default async function ReportsPage({
  searchParams,
}: {
  searchParams: { date?: string };
}) {
  const reportDates = await getReportDates();
  const digests = await getDigests();

  const selectedDate = searchParams.date || reportDates[0];

  // Find corresponding digest info
  const selectedDigest = digests.find(d => {
    // Convert date formats if needed
    const digestDate = d.date;
    return digestDate === selectedDate || d.pdf_path?.includes(selectedDate);
  });

  return (
    <div className="p-8">
      {/* Header */}
      <div className="mb-8">
        <h1 className="text-2xl font-bold text-gray-900">PDF Reports</h1>
        <p className="text-gray-500 mt-1">
          View and download daily research digest reports
        </p>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-4 gap-6">
        {/* Report Calendar/List */}
        <div className="lg:col-span-1">
          <Card>
            <CardHeader>
              <CardTitle className="text-sm font-medium flex items-center gap-2">
                <Calendar className="h-4 w-4" />
                Available Reports
              </CardTitle>
            </CardHeader>
            <CardContent>
              {reportDates.length > 0 ? (
                <div className="space-y-2">
                  {reportDates.map((date) => (
                    <Link
                      key={date}
                      href={`/reports?date=${encodeURIComponent(date)}`}
                      className={`block px-3 py-2 rounded-lg text-sm transition-colors ${
                        selectedDate === date
                          ? "bg-blue-50 text-blue-700 font-medium"
                          : "text-gray-600 hover:bg-gray-50"
                      }`}
                    >
                      <div className="flex items-center justify-between">
                        <span>{date}</span>
                        <FileText className="h-4 w-4" />
                      </div>
                    </Link>
                  ))}
                </div>
              ) : (
                <p className="text-sm text-gray-500 py-4">
                  No reports generated yet. Reports are created when the daily workflow runs.
                </p>
              )}
            </CardContent>
          </Card>

          {/* Digest Info */}
          {selectedDigest && (
            <Card className="mt-4">
              <CardHeader>
                <CardTitle className="text-sm font-medium">
                  Digest Info
                </CardTitle>
              </CardHeader>
              <CardContent className="space-y-3">
                <div>
                  <p className="text-xs text-gray-500">Papers Fetched</p>
                  <p className="font-medium">{selectedDigest.papers_fetched}</p>
                </div>
                <div>
                  <p className="text-xs text-gray-500">WhatsApp</p>
                  <Badge variant={selectedDigest.whatsapp_sent ? "success" : "secondary"}>
                    {selectedDigest.whatsapp_sent ? "Sent" : "Not Sent"}
                  </Badge>
                </div>
                {selectedDigest.workflow_run_id && (
                  <div>
                    <p className="text-xs text-gray-500">Workflow Run</p>
                    <a
                      href={`https://github.com/vickey-kapoor/ai-research-whatsapp-digest/actions/runs/${selectedDigest.workflow_run_id}`}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="text-sm text-blue-600 hover:underline inline-flex items-center gap-1"
                    >
                      View run
                      <ExternalLink className="h-3 w-3" />
                    </a>
                  </div>
                )}
              </CardContent>
            </Card>
          )}
        </div>

        {/* PDF Viewer */}
        <div className="lg:col-span-3">
          <Card className="h-full">
            <CardHeader>
              <div className="flex items-center justify-between">
                <CardTitle className="flex items-center gap-2">
                  <FileText className="h-5 w-5 text-blue-600" />
                  {selectedDate ? `Report: ${selectedDate}` : "Select a Report"}
                </CardTitle>
                {selectedDate && (
                  <a
                    href={`/api/reports/${selectedDate}/ai_research_digest.pdf`}
                    download
                    className="inline-flex items-center gap-1 px-3 py-1.5 bg-blue-600 text-white text-sm rounded-lg hover:bg-blue-700"
                  >
                    Download PDF
                  </a>
                )}
              </div>
            </CardHeader>
            <CardContent>
              {selectedDate ? (
                <div className="bg-gray-100 rounded-lg overflow-hidden" style={{ height: '700px' }}>
                  <iframe
                    src={`/api/reports/${selectedDate}/ai_research_digest.pdf`}
                    className="w-full h-full"
                    title={`Report for ${selectedDate}`}
                  />
                </div>
              ) : (
                <div className="flex items-center justify-center h-96 bg-gray-50 rounded-lg">
                  <p className="text-gray-500">Select a report from the list to view</p>
                </div>
              )}
            </CardContent>
          </Card>
        </div>
      </div>
    </div>
  );
}
