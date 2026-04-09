import {
  BriefingRunResponse,
  EditableSettings,
  EditableSettingsUpdate,
  GmailRunResponse,
  HealthResponse,
  JobsQueueResponse,
  JobsRunResponse,
  JobsStats,
  LinkedInDecisionResponse,
  LinkedInDraft,
  LinkedInPublishResponse,
  LinkedInStatus,
  RunsHistoryResponse,
  SchedulerStatus,
  SystemStatus,
} from "../types/api";

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL ?? "http://localhost:8000";

async function fetchJson<T>(path: string, options?: RequestInit): Promise<T> {
  const response = await fetch(`${API_BASE_URL}${path}`, {
    headers: {
      "Content-Type": "application/json",
      ...(options?.headers ?? {}),
    },
    ...options,
  });

  if (!response.ok) {
    let detail = `Request failed: ${response.status}`;
    try {
      const body = (await response.json()) as { detail?: string };
      if (body.detail) {
        detail = body.detail;
      }
    } catch {
      // keep default error
    }
    throw new Error(detail);
  }

  return (await response.json()) as T;
}

export const apiClient = {
  getHealth: (): Promise<HealthResponse> => fetchJson("/api/health"),
  getStatus: (): Promise<SystemStatus> => fetchJson("/api/status"),
  runJobs: (): Promise<JobsRunResponse> => fetchJson("/api/jobs/run", { method: "POST" }),
  getJobsQueue: (): Promise<JobsQueueResponse> => fetchJson("/api/jobs/queue"),
  getJobsStats: (): Promise<JobsStats> => fetchJson("/api/jobs/stats"),
  runBriefing: (sendToTelegram = false): Promise<BriefingRunResponse> =>
    fetchJson("/api/briefing/run", {
      method: "POST",
      body: JSON.stringify({ send_to_telegram: sendToTelegram }),
    }),
  runGmail: (sendToTelegram = false): Promise<GmailRunResponse> =>
    fetchJson("/api/gmail/run", {
      method: "POST",
      body: JSON.stringify({ send_to_telegram: sendToTelegram }),
    }),
  getLinkedinStatus: (): Promise<LinkedInStatus> => fetchJson("/api/linkedin/status"),
  getLinkedinDraft: (): Promise<LinkedInDraft> => fetchJson("/api/linkedin/draft"),
  generateLinkedinDraft: (): Promise<LinkedInDraft> => fetchJson("/api/linkedin/draft/generate", { method: "POST" }),
  saveLinkedinDraft: (content: string): Promise<LinkedInDraft> =>
    fetchJson("/api/linkedin/draft", { method: "PUT", body: JSON.stringify({ content }) }),
  approveLinkedinDraft: (): Promise<LinkedInDecisionResponse> => fetchJson("/api/linkedin/draft/approve", { method: "POST" }),
  rejectLinkedinDraft: (): Promise<LinkedInDecisionResponse> => fetchJson("/api/linkedin/draft/reject", { method: "POST" }),
  publishLinkedinDraft: (confirmPublish: boolean): Promise<LinkedInPublishResponse> =>
    fetchJson("/api/linkedin/draft/publish", {
      method: "POST",
      body: JSON.stringify({ confirm_publish: confirmPublish }),
    }),
  getEditableSettings: (): Promise<EditableSettings> => fetchJson("/api/settings"),
  updateEditableSettings: (payload: EditableSettingsUpdate): Promise<EditableSettings> =>
    fetchJson("/api/settings", { method: "PUT", body: JSON.stringify(payload) }),
  getRunsHistory: (limit = 25): Promise<RunsHistoryResponse> => fetchJson(`/api/runs?limit=${limit}`),
  getSchedulerStatus: (): Promise<SchedulerStatus> => fetchJson("/api/scheduler/status"),
  startScheduler: (confirmAction: boolean): Promise<SchedulerStatus> =>
    fetchJson("/api/scheduler/start", { method: "POST", body: JSON.stringify({ confirm_action: confirmAction }) }),
  stopScheduler: (confirmAction: boolean): Promise<SchedulerStatus> =>
    fetchJson("/api/scheduler/stop", { method: "POST", body: JSON.stringify({ confirm_action: confirmAction }) }),
};

export { API_BASE_URL };
