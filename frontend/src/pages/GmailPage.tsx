import { useState } from "react";

import { apiClient } from "../api/client";
import { ActivityItem } from "../types/api";

type GmailPageProps = {
  onAddActivity: (entry: Omit<ActivityItem, "id" | "timestamp">) => void;
};

export function GmailPage({ onAddActivity }: GmailPageProps) {
  const [running, setRunning] = useState(false);
  const [summary, setSummary] = useState("");
  const [error, setError] = useState("");

  async function runTriage() {
    setRunning(true);
    setError("");
    try {
      const result = await apiClient.runGmail(false);
      setSummary(result.summary);
      onAddActivity({ action: "Gmail Triage", result: "Triage completed" });
    } catch (err) {
      const msg = err instanceof Error ? err.message : "Failed to run Gmail triage";
      setError(msg);
      onAddActivity({ action: "Gmail Triage", result: msg });
    } finally {
      setRunning(false);
    }
  }

  return (
    <section className="panel">
      <div className="panel-header">
        <h2>Gmail Triage</h2>
        <button onClick={runTriage} disabled={running}>
          {running ? "Running..." : "Run Gmail Triage"}
        </button>
      </div>
      {error && <p className="error-text">{error}</p>}
      {summary ? <pre className="text-output">{summary}</pre> : <p>No triage run yet.</p>}
    </section>
  );
}
