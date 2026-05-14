export interface Domain {
  id: number;
  name: string;
  is_active: boolean;
  requests_per_second: number;
  burst_capacity: number;
  concurrent_requests: number;
  max_retries: number;
  retry_delay: number;
  notes: string;
  created_at: string;
  updated_at: string;
}

export interface ScraperSource {
  id: number;
  name: string;
  domain: number;
  domain_name: string;
  offer_url_prefix: string;
  is_active: boolean;
  notes: string;
  preamble_code: string;
  list_pages_code: string;
  list_items_code: string;
  get_item_code: string;
  created_at: string;
  updated_at: string;
}

export interface Job {
  id: number;
  name: string | null;
  domain: number;
  domain_name: string;
  source: string;
  stage: "list_pages" | "list_items" | "get_item";
  url: string;
  is_active: boolean;
  created_at: string;
  updated_at: string;
}

export interface Schedule {
  id: number;
  name: string;
  cron: string;
  jobs: number[];
  is_active: boolean;
  next_run: string | null;
  created_at: string;
  updated_at: string;
}

export interface Paginated<T> {
  count: number;
  next: string | null;
  previous: string | null;
  results: T[];
}

export type ExecutionStatus = "pending" | "running" | "success" | "failed" | "cancelled";

export interface JobRunLog {
  id: number;
  source: string;
  stage: "list_pages" | "list_items" | "get_item";
  url: string;
  domain_name: string;
  job_run_id: string;
  parent_job_run_id: string | null;
  schedule_run_id: string;
  status: ExecutionStatus;
  metadata: Record<string, unknown>;
  created_at: string;
  updated_at: string;
}

export interface ScheduleRunLog {
  id: number;
  schedule: number;
  schedule_name: string;
  schedule_run_id: string;
  status: ExecutionStatus;
  metadata: Record<string, unknown>;
  created_at: string;
  updated_at: string;
}
