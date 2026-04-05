import { getBacklog, getConfig } from "@/lib/data";
import { Card, CardContent } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import {
  ExternalLink,
  ListTodo,
  Star,
  BookOpen,
  Building2,
} from "lucide-react";

const LAB_COLORS: Record<string, string> = {
  "OpenAI": "border-l-green-500",
  "Anthropic": "border-l-orange-500",
  "Google DeepMind": "border-l-blue-500",
  "Meta AI": "border-l-indigo-500",
};

const LAB_DOT_COLORS: Record<string, string> = {
  "OpenAI": "bg-green-500",
  "Anthropic": "bg-orange-500",
  "Google DeepMind": "bg-blue-500",
  "Meta AI": "bg-indigo-500",
};

export default async function BacklogPage() {
  const backlog = await getBacklog();
  const config = getConfig();

  const totalItems = Object.values(backlog).reduce((sum, items) => sum + items.length, 0);

  // Use the configured labs order, then add any extra labs found in data
  const labOrder = [...config.labs];
  for (const lab of Object.keys(backlog)) {
    if (!labOrder.includes(lab)) labOrder.push(lab);
  }

  return (
    <div className="p-8">
      {/* Header */}
      <div className="mb-8">
        <h1 className="text-2xl font-bold text-gray-900 dark:text-gray-100 flex items-center gap-2">
          <ListTodo className="h-6 w-6 text-blue-600" />
          Backlog
        </h1>
        <p className="text-gray-500 mt-1">
          Product updates to try, grouped by AI lab.
          {totalItems > 0 && <span className="ml-1 font-medium text-gray-700">{totalItems} items</span>}
        </p>
      </div>

      {totalItems === 0 ? (
        <Card>
          <CardContent className="p-12 text-center">
            <ListTodo className="h-12 w-12 text-gray-300 mx-auto mb-4" />
            <p className="text-gray-500 text-lg">Your backlog is empty.</p>
            <p className="text-gray-400 text-sm mt-2">
              New product updates will appear here when fetched. Run the daily workflow to get started.
            </p>
          </CardContent>
        </Card>
      ) : (
        <div className="space-y-8">
          {labOrder.map((lab) => {
            const items = backlog[lab];
            if (!items || items.length === 0) return null;

            const borderColor = LAB_COLORS[lab] || "border-l-gray-400";
            const dotColor = LAB_DOT_COLORS[lab] || "bg-gray-400";

            return (
              <div key={lab}>
                {/* Lab Header */}
                <div className="flex items-center gap-3 mb-4">
                  <div className={`h-3 w-3 rounded-full ${dotColor}`} />
                  <h2 className="text-lg font-semibold text-gray-900 dark:text-gray-100 flex items-center gap-2">
                    <Building2 className="h-5 w-5 text-gray-400" />
                    {lab}
                  </h2>
                  <Badge variant="secondary">{items.length} to try</Badge>
                </div>

                {/* Items */}
                <div className="space-y-3 ml-6">
                  {items.map((item) => (
                    <Card
                      key={item.id}
                      className={`border-l-4 ${borderColor} hover:shadow-md transition-shadow`}
                    >
                      <CardContent className="p-4">
                        <div className="flex items-start justify-between gap-4">
                          <div className="flex-1 min-w-0">
                            <div className="flex items-center gap-2 mb-1">
                              {item.status === "starred" ? (
                                <Star className="h-4 w-4 text-yellow-500 fill-yellow-500 flex-shrink-0" />
                              ) : (
                                <BookOpen className="h-4 w-4 text-gray-400 flex-shrink-0" />
                              )}
                              <h3 className="font-medium text-gray-900 dark:text-gray-100 truncate">
                                {item.title}
                              </h3>
                            </div>
                            <p className="text-sm text-gray-600 line-clamp-2 ml-6">
                              {item.description}
                            </p>
                            <div className="flex flex-wrap gap-2 mt-2 ml-6">
                              {item.topics.slice(0, 3).map((topic) => (
                                <Badge key={topic} variant="outline">
                                  {topic}
                                </Badge>
                              ))}
                              <span className="text-xs text-gray-400 self-center">
                                {item.published_at?.split("T")[0]}
                              </span>
                            </div>
                          </div>
                          <a
                            href={item.url}
                            target="_blank"
                            rel="noopener noreferrer"
                            className="flex-shrink-0 p-2 rounded-lg bg-gray-50 dark:bg-gray-800 hover:bg-blue-50 dark:hover:bg-blue-900/30 text-gray-500 hover:text-blue-600 transition-colors"
                            aria-label={`Open ${item.title} in new tab`}
                          >
                            <ExternalLink className="h-5 w-5" />
                          </a>
                        </div>
                      </CardContent>
                    </Card>
                  ))}
                </div>
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}
