import { useEffect, useState } from "react";

import { apiClient } from "../api/client";
import { LinkedInDraft } from "../types/api";

export function LinkedInPage() {
  const [draft, setDraft] = useState<LinkedInDraft | null>(null);
  const [editorText, setEditorText] = useState("");
  const [loading, setLoading] = useState(true);
  const [busyAction, setBusyAction] = useState("");
  const [error, setError] = useState("");
  const [message, setMessage] = useState("");
  const [publishConfirmed, setPublishConfirmed] = useState(false);

  async function loadDraft() {
    setLoading(true);
    setError("");
    try {
      const payload = await apiClient.getLinkedinDraft();
      setDraft(payload);
      setEditorText(payload.content);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to load LinkedIn draft");
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    loadDraft();
  }, []);

  async function runAction(action: string, fn: () => Promise<void>) {
    setBusyAction(action);
    setError("");
    setMessage("");
    try {
      await fn();
    } catch (err) {
      setError(err instanceof Error ? err.message : `Failed to ${action.toLowerCase()}`);
    } finally {
      setBusyAction("");
    }
  }

  return (
    <section className="panel">
      <div className="panel-header">
        <h2>LinkedIn Review</h2>
        <span>Today: {draft?.today ?? "-"}</span>
      </div>

      {loading && <p>Loading LinkedIn draft...</p>}
      {error && <p className="error-text">{error}</p>}
      {message && <p>{message}</p>}

      {!loading && (
        <>
          <div className="button-row linkedin-actions">
            <button
              onClick={() =>
                runAction("Generate Draft", async () => {
                  const payload = await apiClient.generateLinkedinDraft();
                  setDraft(payload);
                  setEditorText(payload.content);
                  setMessage(payload.exists ? "Draft generated." : "No draft generated for today.");
                })
              }
              disabled={Boolean(busyAction)}
            >
              {busyAction === "Generate Draft" ? "Generating..." : "Generate Draft"}
            </button>

            <button
              className="secondary-button"
              onClick={() =>
                runAction("Save Edits", async () => {
                  const payload = await apiClient.saveLinkedinDraft(editorText);
                  setDraft(payload);
                  setMessage("Draft edits saved.");
                })
              }
              disabled={Boolean(busyAction) || !editorText.trim()}
            >
              {busyAction === "Save Edits" ? "Saving..." : "Save Edits"}
            </button>

            <button
              onClick={() =>
                runAction("Approve", async () => {
                  const payload = await apiClient.approveLinkedinDraft();
                  setDraft(payload.draft);
                  setMessage(payload.message);
                })
              }
              disabled={Boolean(busyAction) || !draft?.exists}
            >
              {busyAction === "Approve" ? "Approving..." : "Approve"}
            </button>

            <button
              className="secondary-button"
              onClick={() =>
                runAction("Reject", async () => {
                  const payload = await apiClient.rejectLinkedinDraft();
                  setDraft(payload.draft);
                  setMessage(payload.message);
                })
              }
              disabled={Boolean(busyAction) || !draft?.exists}
            >
              {busyAction === "Reject" ? "Rejecting..." : "Reject"}
            </button>

            {draft?.publish_supported && (
              <button
                onClick={() =>
                  runAction("Publish", async () => {
                    const payload = await apiClient.publishLinkedinDraft(publishConfirmed);
                    setMessage(payload.message);
                    await loadDraft();
                    setPublishConfirmed(false);
                  })
                }
                disabled={Boolean(busyAction) || draft?.status !== "approved" || !publishConfirmed}
              >
                {busyAction === "Publish" ? "Publishing..." : "Publish"}
              </button>
            )}
          </div>

          {draft && (
            <>
              <ul className="kv-list">
                <li><span>Draft Exists</span><strong>{draft.exists ? "Yes" : "No"}</strong></li>
                <li><span>Review Status</span><strong>{draft.status}</strong></li>
                <li><span>Publish Support</span><strong>{draft.publish_supported ? "Enabled" : "Disabled"}</strong></li>
              </ul>

              <h3 className="linkedin-subtitle">Metadata</h3>
              <pre className="text-output">{JSON.stringify(draft.metadata, null, 2) || "{}"}</pre>

              <h3 className="linkedin-subtitle">Draft Content</h3>
              <textarea
                className="linkedin-editor"
                value={editorText}
                onChange={(event) => setEditorText(event.target.value)}
                placeholder="Generate or paste your LinkedIn draft here..."
                rows={12}
              />

              {draft.publish_supported ? (
                <label className="publish-confirm">
                  <input
                    type="checkbox"
                    checked={publishConfirmed}
                    onChange={(event) => setPublishConfirmed(event.target.checked)}
                  />
                  I explicitly confirm I want to publish this approved post now.
                </label>
              ) : (
                <p className="text-output">Publishing is currently disabled. Configure LINKEDIN_ACCESS_TOKEN and LINKEDIN_PERSON_URN to enable publish API access.</p>
              )}
            </>
          )}
        </>
      )}
    </section>
  );
}
