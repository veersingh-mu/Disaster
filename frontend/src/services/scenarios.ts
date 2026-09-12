import { apiFetch } from './api';
import {
  Scenario,
  ScenarioCreate,
  ScenarioListResponse,
  ScenarioResultsResponse,
  ScenarioUpdate,
  SimulationRun,
  SimulationStatusResponse,
} from '../types/api';

export const scenariosService = {
  async createScenario(payload: ScenarioCreate): Promise<Scenario> {
    return apiFetch<Scenario>('/scenarios', {
      method: 'POST',
      body: JSON.stringify(payload),
    });
  },

  async listScenarios(skip: number = 0, limit: number = 50): Promise<ScenarioListResponse> {
    return apiFetch<ScenarioListResponse>(`/scenarios?skip=${skip}&limit=${limit}`);
  },

  async getScenario(id: string): Promise<Scenario> {
    return apiFetch<Scenario>(`/scenarios/${id}`);
  },

  async updateScenario(id: string, payload: ScenarioUpdate): Promise<Scenario> {
    return apiFetch<Scenario>(`/scenarios/${id}`, {
      method: 'PATCH',
      body: JSON.stringify(payload),
    });
  },

  async deleteScenario(id: string): Promise<void> {
    return apiFetch<void>(`/scenarios/${id}`, {
      method: 'DELETE',
    });
  },

  async triggerSimulation(id: string, mode: string = 'full'): Promise<SimulationRun> {
    return apiFetch<SimulationRun>(`/scenarios/${id}/run`, {
      method: 'POST',
      body: JSON.stringify({ mode }),
    });
  },

  async getSimulationStatus(id: string): Promise<SimulationStatusResponse> {
    return apiFetch<SimulationStatusResponse>(`/scenarios/${id}/status`);
  },

  async getScenarioResults(id: string): Promise<ScenarioResultsResponse> {
    return apiFetch<ScenarioResultsResponse>(`/scenarios/${id}/results`);
  },
};
