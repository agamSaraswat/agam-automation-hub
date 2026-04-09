export type HealthResponse = {
  status: string;
  service: string;
  date: string;
};

export type EnvironmentVarStatus = {
  set: boolean;
  required: boolean;
  description: string;
};

export type JobsStats = {
  total_jobs: number;
  today_queued: number;
  by_status: Record<string, number>;
};

export type LinkedInStatus = {
  status: string;
  today: string;
  queue_file_exists: boolean;
  posted_file_exists: boolean;
  token_set_date: string | null;
  token_age_days: number | null;
  token_warning: string | null;
};

export type SystemStatus = {
  date: string;
  environment: Record<string, EnvironmentVarStatus>;
  jobs: JobsStats;
  linkedin: LinkedInStatus;
};

export type JobsRunResponse = {
  scraped_new_jobs: number;
  tailored_jobs: number;
  queue_size_today: number;
  stats: JobsStats;
};

export type JobQueueItem = {
  id?: number;
  url: string;
  company: string;
  title: string;
  location?: string;
  date_seen?: string;
  status: string;
  source?: string;
};

export type JobsQueueResponse = {
  items: JobQueueItem[];
  count: number;
};

export type BriefingRunResponse = {
  briefing: string;
  sent_to_telegram: boolean;
};

export type GmailRunResponse = {
  summary: string;
  sent_to_telegram: boolean;
};

export type ActivityItem = {
  id: string;
  timestamp: string;
  action: string;
  result: string;
};
