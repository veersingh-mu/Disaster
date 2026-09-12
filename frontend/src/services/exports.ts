import { API_BASE_URL, apiFetch } from './api';
import { ExportCreateRequest, ExportResponse } from '../types/api';

export const exportsService = {
  async createExport(
    scenarioId: string,
    payload: ExportCreateRequest
  ): Promise<ExportResponse> {
    return apiFetch<ExportResponse>(`/scenarios/${scenarioId}/export`, {
      method: 'POST',
      body: JSON.stringify(payload),
    });
  },

  async listScenarioExports(scenarioId: string): Promise<ExportResponse[]> {
    return apiFetch<ExportResponse[]>(`/scenarios/${scenarioId}/exports`);
  },

  async getExportData(exportId: string): Promise<Record<string, unknown>> {
    return apiFetch<Record<string, unknown>>(`/exports/${exportId}/data`);
  },

  async getScenarioCapXmlAlert(scenarioId: string): Promise<string> {
    const token = localStorage.getItem('floodpath_token');
    const headers: Record<string, string> = {};
    if (token) {
      headers['Authorization'] = `Bearer ${token}`;
    }
    const res = await fetch(`${API_BASE_URL}/scenarios/${scenarioId}/alert/cap-xml`, {
      headers,
    });
    if (!res.ok) {
      throw new Error(`Failed to generate CAP XML: ${res.statusText}`);
    }
    return res.text();
  },
};
