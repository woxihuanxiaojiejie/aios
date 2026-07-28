export type SystemStatus =
  | "healthy"
  | "degraded"
  | "unavailable"
  | "not_configured"
  | "unknown";

export type ApplicationStatus = {
  status: SystemStatus;
  name: string;
  version: string | null;
  commit: string | null;
  environment: string | null;
  started_at: string | null;
  checked_at: string;
  message: string | null;
};

export type DatabaseStatus = {
  status: SystemStatus;
  backend: string;
  checked_at: string;
  latency_ms: number | null;
  message: string | null;
};

export type SchedulerStatus = {
  status: SystemStatus;
  running: boolean;
  last_heartbeat_at: string | null;
  heartbeat_age_seconds: number | null;
  message: string | null;
};

export type SchedulerJobStatus = {
  status: SystemStatus;
  enabled: boolean;
  last_started_at: string | null;
  last_completed_at: string | null;
  last_result: string | null;
  last_error: string | null;
  processed_count: number | null;
  success_count: number | null;
  failure_count: number | null;
};

export type QueueStatus = {
  research_due: number;
  settlement_due: number;
  failed_research_runs: number;
  resumable_research_runs: number;
};

export type ProviderStatus = {
  provider: string;
  model: string | null;
  configured: boolean;
  status: SystemStatus;
  message: string | null;
};

export type SystemStatusSummary = {
  generated_at: string;
  overall_status: SystemStatus;
  application: ApplicationStatus;
  database: DatabaseStatus;
  scheduler: SchedulerStatus;
  jobs: Record<string, SchedulerJobStatus>;
  queues: QueueStatus;
  providers: ProviderStatus[];
  issues: string[];
};
