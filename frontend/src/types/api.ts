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

export type LinkedInDraft = {
  today: string;
  exists: boolean;
  content: string;
  metadata: Record<string, unknown>;
  status: string;
  publish_supported: boolean;
};

export type LinkedInDecisionResponse = {
  draft: LinkedInDraft;
  message: string;
};

export type LinkedInPublishResponse = {
  published: boolean;
  message: string;
};


export type PostingTimeWindow = {
  start_hour: number;
  end_hour: number;
};

export type SecretConfigStatus = {
  configured: boolean;
  description: string;
};

export type EditableSettingsUpdate = {
  target_roles: string[];
  locations: string[];
  include_keywords: string[];
  exclude_keywords: string[];
  daily_job_limit: number;
  posting_time_window: PostingTimeWindow;
  job_sources: Record<string, boolean>;
};

export type EditableSettings = {
  target_roles: string[];
  locations: string[];
  include_keywords: string[];
  exclude_keywords: string[];
  daily_job_limit: number;
  posting_time_window: PostingTimeWindow;
  job_sources: Record<string, boolean>;
  secret_status: Record<string, SecretConfigStatus>;
  editable_fields: string[];
  file_based_notes: string[];
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


export type SchedulerJobItem = {
  job_id: string;
  name: string;
  trigger: string;
  next_run_time: string | null;
};

export type SchedulerStatus = {
  running: boolean;
  timezone: string;
  started_at: string | null;
  job_count: number;
  next_run_time: string | null;
  jobs: SchedulerJobItem[];
};

export type RunHistoryItem = {
  run_id: string;
  task_type: string;
  start_time: string;
  end_time: string;
  status: string;
  summary: string;
  error_message: string | null;
};

export type RunsHistoryResponse = {
  items: RunHistoryItem[];
  count: number;
};

export type ActivityItem = {
  id: string;
  timestamp: string;
  action: string;
  result: string;
};
