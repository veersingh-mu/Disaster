/**
 * TypeScript definitions matching FloodPath backend schemas and domain models.
 */

export type BreachType = 'structural' | 'landslide_glof';

export type RunStatus = 'pending' | 'running' | 'succeeded' | 'failed';

export type PipelineStage =
  | 'dem_fetch'
  | 'breach_estimation'
  | 'flood_routing'
  | 'summary_generation';

export type ExportFormat = 'pdf' | 'json';

export interface Scenario {
  id: string;
  user_id: string;
  name: string;
  latitude: number;
  longitude: number;
  breach_type: BreachType;
  dam_height_m: number;
  dam_volume_m3: number;
  simulation_radius_km: number;
  is_dem_estimated: boolean;
  created_at: string;
  updated_at: string;
  latest_run_id?: string | null;
  latest_run_status?: RunStatus | null;
}

export interface ScenarioCreate {
  name: string;
  latitude: number;
  longitude: number;
  breach_type: BreachType;
  dam_height_m: number;
  dam_volume_m3: number;
  simulation_radius_km?: number;
  is_dem_estimated?: boolean;
}

export interface ScenarioUpdate {
  name?: string;
  simulation_radius_km?: number;
}

export interface ScenarioListResponse {
  scenarios: Scenario[];
  total: number;
}

export interface SimulationRun {
  id: string;
  scenario_id: string;
  status: RunStatus;
  mode?: string;
  current_stage?: PipelineStage | null;
  error_stage?: PipelineStage | null;
  error_message?: string | null;
  started_at?: string | null;
  completed_at?: string | null;
  created_at: string;
}

export interface SimulationStatusResponse {
  scenario_id: string;
  run_id: string;
  status: RunStatus;
  mode?: string;
  current_stage?: PipelineStage | null;
  error_stage?: PipelineStage | null;
  error_message?: string | null;
  progress_percent: number;
  started_at?: string | null;
  completed_at?: string | null;
  elapsed_seconds?: number | null;
}

export interface FloodResultStep {
  id: string;
  time_step_minutes: number;
  flood_extent: GeoJSON.GeoJsonObject | Record<string, unknown>;
  max_depth_m?: number | null;
}

export interface AffectedSettlementItem {
  settlement_id: string;
  name: string;
  district: string;
  state: string;
  population?: number | null;
  arrival_time_minutes: number;
  estimated_depth_m?: number | null;
}

export interface ScenarioResultsResponse {
  scenario_id: string;
  simulation_run_id: string;
  status: RunStatus;
  mode?: string;
  is_surrogate?: boolean;
  summary_text?: string | null;
  time_steps: FloodResultStep[];
  affected_settlements: AffectedSettlementItem[];
  total_affected_settlements: number;
  peak_depth_m?: number | null;
  arrival_time_first_settlement_minutes?: number | null;
}

export interface CaseStudy {
  id: string;
  scenario_id: string;
  simulation_run_id: string;
  event_year: number;
  description: string;
  source_reference?: string | null;
  created_at: string;
  name?: string | null;
  breach_type?: BreachType | null;
  dam_height_m?: number | null;
  dam_volume_m3?: number | null;
  simulation_radius_km?: number | null;
  latitude?: number | null;
  longitude?: number | null;
}

export interface CaseStudyListResponse {
  case_studies: CaseStudy[];
  total: number;
}

export interface DEMPreviewResponse {
  latitude: number;
  longitude: number;
  elevation_m: number;
  slope_degrees?: number | null;
  estimated_dam_height_m: number;
  estimated_dam_volume_m3: number;
  source: string;
  coverage_available: boolean;
  resolution_m?: number;
  is_cached?: boolean;
}

export interface ExportCreateRequest {
  format: ExportFormat;
}

export interface ExportResponse {
  id: string;
  simulation_run_id: string;
  user_id: string;
  file_url: string;
  format: ExportFormat;
  created_at: string;
}
