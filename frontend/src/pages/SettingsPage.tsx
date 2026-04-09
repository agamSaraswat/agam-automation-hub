import { useEffect, useMemo, useState } from "react";

import { apiClient } from "../api/client";
import { EditableSettings, EditableSettingsUpdate } from "../types/api";

function splitLines(value: string): string[] {
  return value
    .split(/\r?\n|,/)
    .map((item) => item.trim())
    .filter(Boolean);
}

function joinLines(value: string[]): string {
  return value.join("\n");
}

function toUpdatePayload(settings: EditableSettings): EditableSettingsUpdate {
  return {
    target_roles: settings.target_roles,
    locations: settings.locations,
    include_keywords: settings.include_keywords,
    exclude_keywords: settings.exclude_keywords,
    daily_job_limit: settings.daily_job_limit,
    posting_time_window: settings.posting_time_window,
    job_sources: settings.job_sources,
  };
}

export function SettingsPage() {
  const [settings, setSettings] = useState<EditableSettings | null>(null);
  const [draft, setDraft] = useState<EditableSettings | null>(null);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState("");
  const [message, setMessage] = useState("");

  useEffect(() => {
    async function loadSettings() {
      setLoading(true);
      setError("");
      try {
        const payload = await apiClient.getEditableSettings();
        setSettings(payload);
        setDraft(payload);
      } catch (err) {
        setError(err instanceof Error ? err.message : "Failed to load settings");
      } finally {
        setLoading(false);
      }
    }

    loadSettings();
  }, []);

  const dirty = useMemo(() => {
    if (!settings || !draft) {
      return false;
    }
    return JSON.stringify(toUpdatePayload(settings)) !== JSON.stringify(toUpdatePayload(draft));
  }, [settings, draft]);

  function updateListField(field: "target_roles" | "locations" | "include_keywords" | "exclude_keywords", raw: string) {
    if (!draft) {
      return;
    }
    setDraft({ ...draft, [field]: splitLines(raw) });
  }

  async function handleSave() {
    if (!draft) {
      return;
    }

    if (draft.posting_time_window.start_hour >= draft.posting_time_window.end_hour) {
      setError("Posting time window start must be earlier than end.");
      return;
    }

    setSaving(true);
    setError("");
    setMessage("");
    try {
      const updated = await apiClient.updateEditableSettings(toUpdatePayload(draft));
      setSettings(updated);
      setDraft(updated);
      setMessage("Settings saved successfully.");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to save settings");
    } finally {
      setSaving(false);
    }
  }

  function handleCancel() {
    if (!settings) {
      return;
    }
    setDraft(settings);
    setError("");
    setMessage("Unsaved changes were discarded.");
  }

  function handleReset() {
    if (!settings) {
      return;
    }
    setDraft(settings);
    setError("");
    setMessage("Form reset to currently saved values.");
  }

  return (
    <section className="panel">
      <h2>Settings</h2>
      <p className="settings-help">Update common non-secret configuration without editing YAML manually.</p>

      {loading && <p>Loading settings...</p>}
      {error && <p className="error-text">{error}</p>}
      {message && <p>{message}</p>}

      {draft && (
        <div className="settings-grid">
          <label>
            Target Roles (one per line)
            <textarea
              value={joinLines(draft.target_roles)}
              onChange={(event) => updateListField("target_roles", event.target.value)}
              rows={5}
            />
          </label>

          <label>
            Locations (one per line)
            <textarea
              value={joinLines(draft.locations)}
              onChange={(event) => updateListField("locations", event.target.value)}
              rows={4}
            />
          </label>

          <label>
            Include Keywords (one per line)
            <textarea
              value={joinLines(draft.include_keywords)}
              onChange={(event) => updateListField("include_keywords", event.target.value)}
              rows={5}
            />
          </label>

          <label>
            Exclude Keywords (one per line)
            <textarea
              value={joinLines(draft.exclude_keywords)}
              onChange={(event) => updateListField("exclude_keywords", event.target.value)}
              rows={5}
            />
          </label>

          <label>
            Daily Job Limit
            <input
              type="number"
              min={1}
              max={200}
              value={draft.daily_job_limit}
              onChange={(event) => setDraft({ ...draft, daily_job_limit: Number(event.target.value) || 1 })}
            />
          </label>

          <div className="time-window-row">
            <label>
              Posting Window Start (hour)
              <input
                type="number"
                min={0}
                max={23}
                value={draft.posting_time_window.start_hour}
                onChange={(event) =>
                  setDraft({
                    ...draft,
                    posting_time_window: {
                      ...draft.posting_time_window,
                      start_hour: Number(event.target.value) || 0,
                    },
                  })
                }
              />
            </label>
            <label>
              Posting Window End (hour)
              <input
                type="number"
                min={0}
                max={23}
                value={draft.posting_time_window.end_hour}
                onChange={(event) =>
                  setDraft({
                    ...draft,
                    posting_time_window: {
                      ...draft.posting_time_window,
                      end_hour: Number(event.target.value) || 0,
                    },
                  })
                }
              />
            </label>
          </div>

          <div>
            <h3 className="linkedin-subtitle">Job Sources</h3>
            <div className="source-grid">
              {Object.entries(draft.job_sources).map(([source, enabled]) => (
                <label key={source} className="toggle-row">
                  <input
                    type="checkbox"
                    checked={enabled}
                    onChange={(event) =>
                      setDraft({
                        ...draft,
                        job_sources: {
                          ...draft.job_sources,
                          [source]: event.target.checked,
                        },
                      })
                    }
                  />
                  {source}
                </label>
              ))}
            </div>
          </div>

          <div>
            <h3 className="linkedin-subtitle">Secret Configuration Status</h3>
            <ul className="kv-list">
              {Object.entries(draft.secret_status).map(([key, value]) => (
                <li key={key}>
                  <span>{key}</span>
                  <strong>{value.configured ? "Configured" : "Not configured"}</strong>
                </li>
              ))}
            </ul>
          </div>

          <div>
            <h3 className="linkedin-subtitle">Still file-based</h3>
            <ul className="settings-notes">
              {draft.file_based_notes.map((note) => (
                <li key={note}>{note}</li>
              ))}
            </ul>
          </div>

          <div className="button-row">
            <button onClick={handleSave} disabled={saving || !dirty}>
              {saving ? "Saving..." : "Save Settings"}
            </button>
            <button className="secondary-button" onClick={handleCancel} disabled={saving || !dirty}>
              Cancel Changes
            </button>
            <button className="secondary-button" onClick={handleReset} disabled={saving}>
              Reset Form
            </button>
          </div>
        </div>
      )}
    </section>
  );
}
