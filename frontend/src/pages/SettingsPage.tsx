import { useEffect, useState } from "react";

import { apiClient } from "../api/client";
import { SystemStatus } from "../types/api";

export function SettingsPage() {
  const [status, setStatus] = useState<SystemStatus | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  useEffect(() => {
    async function loadStatus() {
      setLoading(true);
      setError("");
      try {
        setStatus(await apiClient.getStatus());
      } catch (err) {
        setError(err instanceof Error ? err.message : "Failed to load settings");
      } finally {
        setLoading(false);
      }
    }

    loadStatus();
  }, []);

  return (
    <section className="panel">
      <h2>Environment Configuration</h2>
      {loading && <p>Loading settings...</p>}
      {error && <p className="error-text">{error}</p>}
      {status && (
        <div className="table-wrap">
          <table>
            <thead>
              <tr>
                <th>Variable</th>
                <th>Configured</th>
                <th>Required</th>
                <th>Description</th>
              </tr>
            </thead>
            <tbody>
              {Object.entries(status.environment).map(([key, value]) => (
                <tr key={key}>
                  <td>{key}</td>
                  <td>{value.set ? "Yes" : "No"}</td>
                  <td>{value.required ? "Yes" : "No"}</td>
                  <td>{value.description}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </section>
  );
}
