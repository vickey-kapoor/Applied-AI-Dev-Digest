import { describe, it, expect, vi, beforeEach } from "vitest";
import { getPapers, getDigests, getConfig, getBacklog, getStats } from "@/lib/data";

// Mock global fetch
const mockFetch = vi.fn();
vi.stubGlobal("fetch", mockFetch);

beforeEach(() => {
  mockFetch.mockReset();
});

describe("getPapers", () => {
  it("returns papers from JSON response", async () => {
    const papers = [
      {
        id: "1",
        title: "Test Paper",
        description: "Test",
        source: "OpenAI",
        url: "https://openai.com/test",
        published_at: "2026-03-17",
        fetched_at: "2026-03-17T00:00:00Z",
        authors: "Author",
        topics: ["API Update"],
        ranking_score: 8,
        status: "unread",
      },
    ];

    mockFetch.mockResolvedValueOnce({
      ok: true,
      json: async () => ({ papers }),
    });

    const result = await getPapers();
    expect(result).toEqual(papers);
  });

  it("returns empty array on fetch failure", async () => {
    mockFetch.mockRejectedValueOnce(new Error("Network error"));

    const result = await getPapers();
    expect(result).toEqual([]);
  });

  it("returns empty array when response has no papers key", async () => {
    mockFetch.mockResolvedValueOnce({
      ok: true,
      json: async () => ({}),
    });

    const result = await getPapers();
    expect(result).toEqual([]);
  });

  it("tries fallback branch when first fails", async () => {
    mockFetch
      .mockResolvedValueOnce({ ok: false }) // master fails
      .mockResolvedValueOnce({
        ok: true,
        json: async () => ({ papers: [{ id: "1", title: "Fallback" }] }),
      }); // main succeeds

    const result = await getPapers();
    expect(result).toHaveLength(1);
    expect(mockFetch).toHaveBeenCalledTimes(2);
  });
});

describe("getDigests", () => {
  it("returns digests from JSON response", async () => {
    const digests = [
      {
        date: "2026-03-17",
        top_paper_id: "1",
        papers_fetched: 5,
        pdf_path: "reports/17-Mar/test.pdf",
        telegram_sent: true,
        workflow_run_id: "123",
      },
    ];

    mockFetch.mockResolvedValueOnce({
      ok: true,
      json: async () => ({ digests }),
    });

    const result = await getDigests();
    expect(result).toEqual(digests);
  });

  it("returns empty array on failure", async () => {
    mockFetch.mockRejectedValueOnce(new Error("fail"));
    const result = await getDigests();
    expect(result).toEqual([]);
  });
});

describe("getConfig", () => {
  it("returns static config with expected fields", () => {
    const config = getConfig();
    expect(config.labs).toContain("OpenAI");
    expect(config.labs).toContain("Google DeepMind");
    expect(config.schedule).toBe("0 16 * * *");
    expect(config.telegram_enabled).toBe(true);
  });
});

describe("getBacklog", () => {
  it("groups unread papers by source", async () => {
    const papers = [
      {
        id: "1",
        title: "Paper 1",
        description: "",
        source: "OpenAI",
        url: "",
        published_at: "2026-03-17",
        fetched_at: "2026-03-17T00:00:00Z",
        authors: "",
        topics: [],
        ranking_score: 0,
        status: "unread",
      },
      {
        id: "2",
        title: "Paper 2",
        description: "",
        source: "Anthropic",
        url: "",
        published_at: "2026-03-16",
        fetched_at: "2026-03-16T00:00:00Z",
        authors: "",
        topics: [],
        ranking_score: 0,
        status: "unread",
      },
      {
        id: "3",
        title: "Paper 3",
        description: "",
        source: "OpenAI",
        url: "",
        published_at: "2026-03-15",
        fetched_at: "2026-03-15T00:00:00Z",
        authors: "",
        topics: [],
        ranking_score: 0,
        status: "read", // should be excluded
      },
    ];

    mockFetch.mockResolvedValueOnce({
      ok: true,
      json: async () => ({ papers }),
    });

    const backlog = await getBacklog();
    expect(backlog["OpenAI"]).toHaveLength(1);
    expect(backlog["Anthropic"]).toHaveLength(1);
    expect(backlog["OpenAI"][0].id).toBe("1");
  });
});

describe("getStats", () => {
  it("calculates correct stats", async () => {
    const today = new Date().toISOString().split("T")[0];
    const papers = [
      {
        id: "1",
        title: "Today's Paper",
        description: "",
        source: "OpenAI",
        url: "",
        published_at: today,
        fetched_at: `${today}T12:00:00Z`,
        authors: "",
        topics: [],
        ranking_score: 0,
        status: "unread",
      },
      {
        id: "2",
        title: "Old Paper",
        description: "",
        source: "Anthropic",
        url: "",
        published_at: "2026-01-01",
        fetched_at: "2026-01-01T00:00:00Z",
        authors: "",
        topics: [],
        ranking_score: 0,
        status: "starred",
      },
    ];
    const digests = [
      { date: today, top_paper_id: "1", papers_fetched: 5, pdf_path: "", telegram_sent: true, workflow_run_id: "" },
    ];

    // getPapers call
    mockFetch.mockResolvedValueOnce({
      ok: true,
      json: async () => ({ papers }),
    });
    // getDigests call
    mockFetch.mockResolvedValueOnce({
      ok: true,
      json: async () => ({ digests }),
    });

    const stats = await getStats();
    expect(stats.totalPapers).toBe(2);
    expect(stats.todaysPapers).toBe(1);
    expect(stats.totalDigests).toBe(1);
    expect(stats.unreadCount).toBe(1);
    expect(stats.starredCount).toBe(1);
  });
});
