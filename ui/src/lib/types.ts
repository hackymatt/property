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

export type SourceKind = "PORTAL_LISTING" | "FILE_REGISTRY";
export type PropertyType = "APARTMENT" | "HOUSE" | "LAND" | "COMMERCIAL";

/**
 * Stage names are plain strings, not a closed union: the vocabulary varies
 * per source_kind (portals use list_pages/list_items/get_item, file
 * registries use discover/download/extract/transform/load) and new kinds
 * can add their own. STAGE_PRESETS in components/sources/SourceDialog.tsx
 * holds the known ones for convenience only.
 */
export interface ScraperSourceStage {
  id?: number;
  stage_name: string;
  order: number;
  /** Points at a Stage class registered in the scraper repo's STAGE_REGISTRY, e.g. "otodom.ListPagesStage". */
  code_ref: string;
}

export interface ScraperSource {
  id: number;
  name: string;
  domain: number;
  domain_name: string;
  source_kind: SourceKind;
  property_type: PropertyType;
  offer_url_prefix: string;
  /** Source-level settings available to every stage, e.g. {"layer": "transakcje_lokale"} for RCN. */
  config: Record<string, unknown>;
  is_active: boolean;
  notes: string;
  stages: ScraperSourceStage[];
  created_at: string;
  updated_at: string;
}

export interface Job {
  id: number;
  name: string | null;
  domain: number;
  domain_name: string;
  source: string;
  /** Must match one of the source's ScraperSourceStage.stage_name values. */
  stage: string;
  url: string;
  /** Source-specific input for the first stage, e.g. {"teryt_codes": "all"} for RCN. */
  params: Record<string, unknown>;
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
  stage: string;
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
