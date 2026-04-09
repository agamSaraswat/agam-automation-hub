import { useEffect, useState } from "react";

import { apiClient } from "../api/client";
import { RunHistoryItem } from "../types/api";

export function RunsLogsPage() {
  const [runs, setRuns] = useState<RunHistoryItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  async function loadRuns() {
    setLoading(true);
    setError("");
    try {
      const payload = await apiClient.getRunsHistory(40);
      setRuns(payload.items);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to load run history");
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    loadRuns();
  }, []);

  return (
    <section className="panel">
      <div className="panel-header">
        <h2>Runs & Logs</h2>
        <button className="secondary-button" onClick={loadRuns} disabled={loading}>
          {loading ? "Refreshing..." : "Refresh"}
        </button>
      </div>

      {loading && <p>Loading runs...</p>}
      {error && <p className="error-text">{error}</p>}

      {!loading && runs.length === 0 && <p>No recent backend runs yet.</p>}

      {!loading && runs.length > 0 && (
        <ul className="activity-list">
          {runs.map((run) => (
            <li key={run.run_id} className={run.status === "failed" ? "run-failed" : ""}>
              <strong>{run.task_type}</strong>
              <span>{run.summary}</span>
              <small>Run ID: {run.run_id}</small>
              <small>Started: {new Date(run.start_time).toLocaleString()}</small>
              <small>Ended: {new Date(run.end_time).toLocaleString()}</small>
              <small>Status: {run.status}</small>
              {run.error_message && <pre className="run-error">{run.error_message}</pre>}
            </li>
          ))}
        </ul>
      )}
    </section>
  );
}
