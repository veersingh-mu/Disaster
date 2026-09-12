import { apiFetch, ApiFetchError } from './api';
import {
  Scenario,
  ScenarioCreate,
  ScenarioListResponse,
  ScenarioResultsResponse,
  ScenarioUpdate,
  SimulationRun,
  SimulationStatusResponse,
} from '../types/api';
import {
  deleteLocalScenario,
  generateBenchmarkResults,
  getLocalScenarios,
  saveLocalScenario,
} from './mockData';

export const scenariosService = {
  async createScenario(payload: ScenarioCreate): Promise<Scenario> {
    try {
      return await apiFetch<Scenario>('/scenarios', {
        method: 'POST',
        body: JSON.stringify(payload),
      });
    } catch (err: unknown) {
      if ((err as ApiFetchError)?.isNetworkError) {
        const id = `scenario-${Date.now()}`;
        const newScenario: Scenario = {
          id,
          user_id: '00000000-0000-0000-0000-000000000001',
          name: payload.name,
          latitude: payload.latitude,
          longitude: payload.longitude,
          breach_type: payload.breach_type,
          dam_height_m: payload.dam_height_m,
          dam_volume_m3: payload.dam_volume_m3,
          simulation_radius_km: payload.simulation_radius_km || 35.0,
          is_dem_estimated: payload.is_dem_estimated || false,
          created_at: new Date().toISOString(),
          updated_at: new Date().toISOString(),
          latest_run_id: `run-${id}`,
          latest_run_status: 'pending',
        };
        saveLocalScenario(newScenario);
        return newScenario;
      }
      throw err;
    }
  },

  async listScenarios(skip: number = 0, limit: number = 50): Promise<ScenarioListResponse> {
    try {
      return await apiFetch<ScenarioListResponse>(`/scenarios?skip=${skip}&limit=${limit}`);
    } catch (err: unknown) {
      if ((err as ApiFetchError)?.isNetworkError) {
        const all = getLocalScenarios();
        const paged = all.slice(skip, skip + limit);
        return {
          scenarios: paged,
          total: all.length,
        };
      }
      throw err;
    }
  },

  async getScenario(id: string): Promise<Scenario> {
    try {
      return await apiFetch<Scenario>(`/scenarios/${id}`);
    } catch (err: unknown) {
      if ((err as ApiFetchError)?.isNetworkError) {
        const all = getLocalScenarios();
        const found = all.find((s) => s.id === id);
        if (found) return found;
      }
      throw err;
    }
  },

  async updateScenario(id: string, payload: ScenarioUpdate): Promise<Scenario> {
    try {
      return await apiFetch<Scenario>(`/scenarios/${id}`, {
        method: 'PATCH',
        body: JSON.stringify(payload),
      });
    } catch (err: unknown) {
      if ((err as ApiFetchError)?.isNetworkError) {
        const all = getLocalScenarios();
        const found = all.find((s) => s.id === id);
        if (found) {
          if (payload.name) found.name = payload.name;
          if (payload.simulation_radius_km) found.simulation_radius_km = payload.simulation_radius_km;
          found.updated_at = new Date().toISOString();
          saveLocalScenario(found);
          return found;
        }
      }
      throw err;
    }
  },

  async deleteScenario(id: string): Promise<void> {
    try {
      await apiFetch<void>(`/scenarios/${id}`, {
        method: 'DELETE',
      });
    } catch (err: unknown) {
      if ((err as ApiFetchError)?.isNetworkError) {
        deleteLocalScenario(id);
        return;
      }
      throw err;
    }
  },

  async triggerSimulation(id: string, mode: string = 'full'): Promise<SimulationRun> {
    try {
      return await apiFetch<SimulationRun>(`/scenarios/${id}/run`, {
        method: 'POST',
        body: JSON.stringify({ mode }),
      });
    } catch (err: unknown) {
      if ((err as ApiFetchError)?.isNetworkError) {
        const all = getLocalScenarios();
        const found = all.find((s) => s.id === id);
        if (found) {
          found.latest_run_status = 'succeeded';
          found.latest_run_id = `run-${id}`;
          saveLocalScenario(found);
        }
        return {
          id: `run-${id}`,
          scenario_id: id,
          status: 'succeeded',
          mode,
          current_stage: 'summary_generation',
          created_at: new Date().toISOString(),
          started_at: new Date().toISOString(),
          completed_at: new Date().toISOString(),
        };
      }
      throw err;
    }
  },

  async getSimulationStatus(id: string): Promise<SimulationStatusResponse> {
    try {
      return await apiFetch<SimulationStatusResponse>(`/scenarios/${id}/status`);
    } catch (err: unknown) {
      if ((err as ApiFetchError)?.isNetworkError) {
        return {
          scenario_id: id,
          run_id: `run-${id}`,
          status: 'succeeded',
          progress_percent: 100,
          current_stage: 'summary_generation',
          elapsed_seconds: 2,
        };
      }
      throw err;
    }
  },

  async getScenarioResults(id: string): Promise<ScenarioResultsResponse> {
    try {
      return await apiFetch<ScenarioResultsResponse>(`/scenarios/${id}/results`);
    } catch (err: unknown) {
      if ((err as ApiFetchError)?.isNetworkError) {
        const all = getLocalScenarios();
        const found = all.find((s) => s.id === id);
        return generateBenchmarkResults(
          id,
          found?.name || 'Dam Breach Scenario',
          found?.latitude || 30.3833,
          found?.longitude || 79.7333
        );
      }
      throw err;
    }
  },
};

