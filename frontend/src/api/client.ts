import {
  BriefingRunResponse,
  GmailRunResponse,
  HealthResponse,
  JobsQueueResponse,
  JobsRunResponse,
  JobsStats,
  LinkedInStatus,
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
};

export { API_BASE_URL };
