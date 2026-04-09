import { useEffect, useState } from "react";

import { apiClient } from "../api/client";
import { LinkedInStatus } from "../types/api";

export function LinkedInPage() {
  const [status, setStatus] = useState<LinkedInStatus | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  useEffect(() => {
    async function loadStatus() {
      setLoading(true);
      setError("");
      try {
        setStatus(await apiClient.getLinkedinStatus());
      } catch (err) {
        setError(err instanceof Error ? err.message : "Failed to load LinkedIn status");
      } finally {
        setLoading(false);
      }
    }

    loadStatus();
  }, []);

  return (
    <section className="panel">
      <h2>LinkedIn Status</h2>
      {loading && <p>Loading LinkedIn status...</p>}
      {error && <p className="error-text">{error}</p>}
      {status && (
        <ul className="kv-list">
          <li><span>Status</span><strong>{status.status}</strong></li>
          <li><span>Queue Draft</span><strong>{status.queue_file_exists ? "Yes" : "No"}</strong></li>
          <li><span>Posted Today</span><strong>{status.posted_file_exists ? "Yes" : "No"}</strong></li>
          <li><span>Token Age</span><strong>{status.token_age_days ?? "N/A"}</strong></li>
          <li><span>Token Warning</span><strong>{status.token_warning ?? "None"}</strong></li>
        </ul>
      )}
    </section>
  );
}
