import { useEffect, useMemo, useState } from "react";

import { apiClient } from "../api/client";
import { ActivityItem, JobQueueItem, JobsStats } from "../types/api";

type JobsPageProps = {
  onAddActivity: (entry: Omit<ActivityItem, "id" | "timestamp">) => void;
};

export function JobsPage({ onAddActivity }: JobsPageProps) {
  const [queue, setQueue] = useState<JobQueueItem[]>([]);
  const [stats, setStats] = useState<JobsStats | null>(null);
  const [statusFilter, setStatusFilter] = useState<string>("all");
  const [sourceFilter, setSourceFilter] = useState<string>("all");
  const [searchText, setSearchText] = useState("");
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [running, setRunning] = useState(false);

  async function load() {
    setLoading(true);
    setError("");
    try {
      const [queueResponse, statsResponse] = await Promise.all([
        apiClient.getJobsQueue(),
        apiClient.getJobsStats(),
      ]);
      setQueue(queueResponse.items);
      setStats(statsResponse);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to load jobs");
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    load();
  }, []);

  const uniqueStatuses = useMemo(() => {
    const values = new Set(queue.map((job) => (job.status || "").trim()).filter(Boolean));
    return Array.from(values).sort((a, b) => a.localeCompare(b));
  }, [queue]);

  const uniqueSources = useMemo(() => {
    const values = new Set(queue.map((job) => (job.source || "").trim()).filter(Boolean));
    return Array.from(values).sort((a, b) => a.localeCompare(b));
  }, [queue]);

  const filteredQueue = useMemo(() => {
    const query = searchText.trim().toLowerCase();
    return queue.filter((job) => {
      const matchesStatus = statusFilter === "all" || job.status === statusFilter;
      const source = job.source || "";
      const matchesSource = sourceFilter === "all" || source === sourceFilter;
      const haystack = `${job.title} ${job.company} ${job.location || ""} ${source}`.toLowerCase();
      const matchesSearch = !query || haystack.includes(query);
      return matchesStatus && matchesSource && matchesSearch;
    });
  }, [queue, searchText, sourceFilter, statusFilter]);

  const summaryCards = useMemo(() => {
    const byStatus = filteredQueue.reduce<Record<string, number>>((acc, job) => {
      const key = job.status || "unknown";
      acc[key] = (acc[key] ?? 0) + 1;
      return acc;
    }, {});
    return {
      totalToday: queue.length,
      visible: filteredQueue.length,
      queued: byStatus.queued ?? 0,
      tailored: byStatus.tailored ?? 0,
    };
  }, [filteredQueue, queue.length]);

  async function runPipeline() {
    setRunning(true);
    try {
      const result = await apiClient.runJobs();
      onAddActivity({
        action: "Jobs Pipeline",
        result: `Scraped ${result.scraped_new_jobs}, tailored ${result.tailored_jobs}`,
      });
      await load();
    } catch (err) {
      const msg = err instanceof Error ? err.message : "Failed to run jobs pipeline";
      onAddActivity({ action: "Jobs Pipeline", result: msg });
      setError(msg);
    } finally {
      setRunning(false);
    }
  }

  return (
    <div className="page-stack">
      <section className="grid-cards">
        <article className="status-card">
          <p className="status-card-title">Today (queue endpoint)</p>
          <p className="status-card-value">{summaryCards.totalToday}</p>
        </article>
        <article className="status-card">
          <p className="status-card-title">Visible after filters</p>
          <p className="status-card-value">{summaryCards.visible}</p>
        </article>
        <article className="status-card">
          <p className="status-card-title">Queued</p>
          <p className="status-card-value">{summaryCards.queued}</p>
        </article>
        <article className="status-card">
          <p className="status-card-title">Tailored</p>
          <p className="status-card-value">{summaryCards.tailored}</p>
        </article>
      </section>

      <section className="panel">
        <div className="panel-header">
          <h2>Job Queue</h2>
          <button onClick={runPipeline} disabled={running}>
            {running ? "Running..." : "Run Jobs Pipeline"}
          </button>
        </div>
        <div className="filters-row">
          <label>
            Status
            <select value={statusFilter} onChange={(e) => setStatusFilter(e.target.value)}>
              <option value="all">All</option>
              {uniqueStatuses.map((statusValue) => (
                <option value={statusValue} key={statusValue}>
                  {statusValue}
                </option>
              ))}
            </select>
          </label>
          <label>
            Source
            <select value={sourceFilter} onChange={(e) => setSourceFilter(e.target.value)}>
              <option value="all">All</option>
              {uniqueSources.map((sourceValue) => (
                <option value={sourceValue} key={sourceValue}>
                  {sourceValue}
                </option>
              ))}
            </select>
          </label>
          <label className="search-field">
            Search
            <input
              type="search"
              value={searchText}
              placeholder="Title, company, location..."
              onChange={(e) => setSearchText(e.target.value)}
            />
          </label>
        </div>
        {loading && <p>Loading jobs...</p>}
        {error && <p className="error-text">{error}</p>}
        {!loading && !error && queue.length === 0 && <p>No queued jobs yet for today.</p>}
        {!loading && !error && queue.length > 0 && filteredQueue.length === 0 && (
          <p>No jobs match the current filters.</p>
        )}
        {!loading && !error && filteredQueue.length > 0 && (
          <div className="table-wrap">
            <table>
              <thead>
                <tr>
                  <th>Status</th>
                  <th>Title</th>
                  <th>Company</th>
                  <th>Location</th>
                  <th>Source</th>
                </tr>
              </thead>
              <tbody>
                {filteredQueue.map((job, index) => (
                  <tr key={`${job.url}-${index}`}>
                    <td>{job.status}</td>
                    <td>{job.title}</td>
                    <td>{job.company}</td>
                    <td>{job.location || "—"}</td>
                    <td>{job.source || "—"}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </section>

      <section className="panel">
        <h2>Pipeline Stats</h2>
        {!stats ? <p>No stats available.</p> : (
          <ul className="kv-list">
            <li><span>Total Jobs</span><strong>{stats.total_jobs}</strong></li>
            <li><span>Today's Queue</span><strong>{stats.today_queued}</strong></li>
            {Object.entries(stats.by_status).map(([status, count]) => (
              <li key={status}><span>{status}</span><strong>{count}</strong></li>
            ))}
          </ul>
        )}
      </section>
    </div>
  );
}
