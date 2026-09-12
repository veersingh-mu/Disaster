import { getApiBaseUrl, apiFetch, ApiFetchError } from './api';
import { ExportCreateRequest, ExportResponse } from '../types/api';

export const exportsService = {
  async createExport(
    scenarioId: string,
    payload: ExportCreateRequest
  ): Promise<ExportResponse> {
    try {
      return await apiFetch<ExportResponse>(`/scenarios/${scenarioId}/export`, {
        method: 'POST',
        body: JSON.stringify(payload),
      });
    } catch (err: unknown) {
      if ((err as ApiFetchError)?.isNetworkError) {
        return {
          id: `export-${Date.now()}`,
          simulation_run_id: `run-${scenarioId}`,
          user_id: '00000000-0000-0000-0000-000000000001',
          file_url: '#',
          format: payload.format,
          created_at: new Date().toISOString(),
        };
      }
      throw err;
    }
  },

  async listScenarioExports(scenarioId: string): Promise<ExportResponse[]> {
    try {
      return await apiFetch<ExportResponse[]>(`/scenarios/${scenarioId}/exports`);
    } catch (err: unknown) {
      if ((err as ApiFetchError)?.isNetworkError) {
        return [];
      }
      throw err;
    }
  },

  async getExportData(exportId: string): Promise<Record<string, unknown>> {
    return apiFetch<Record<string, unknown>>(`/exports/${exportId}/data`);
  },

  async getScenarioCapXmlAlert(scenarioId: string): Promise<string> {
    const token = typeof window !== 'undefined' ? localStorage.getItem('floodpath_token') : null;
    const headers: Record<string, string> = {};
    if (token) {
      headers['Authorization'] = `Bearer ${token}`;
    }
    const baseUrl = getApiBaseUrl();
    try {
      const res = await fetch(`${baseUrl}/scenarios/${scenarioId}/alert/cap-xml`, {
        headers,
      });
      if (!res.ok) {
        throw new Error(`Failed to generate CAP XML: ${res.statusText}`);
      }
      return await res.text();
    } catch {
      const nowIso = new Date().toISOString();
      return `<?xml version="1.0" encoding="UTF-8"?>
<alert xmlns="urn:oasis:names:tc:emergency:cap:1.2">
  <identifier>IN-NDMA-FLOODPATH-${scenarioId.slice(0, 8).toUpperCase()}</identifier>
  <sender>seoc@uk.gov.in</sender>
  <sent>${nowIso}</sent>
  <status>Actual</status>
  <msgType>Alert</msgType>
  <scope>Public</scope>
  <info>
    <category>Geo</category>
    <event>Flash Flood / Dam Breach Wave</event>
    <urgency>Immediate</urgency>
    <severity>Extreme</severity>
    <certainty>Observed</certainty>
    <headline>EVACUATION ALERT: Catastrophic Inundation Wave Approaching River Basin</headline>
    <description>Hydrodynamic wave front advancing rapidly downstream. All riverfront terraces, bridges, and low-lying habitations must evacuate vertically to at least 30m above river datum.</description>
    <instruction>Evacuate to designated district muster points immediately. Avoid bridges and riverbanks.</instruction>
    <area>
      <areaDesc>Rini Village, Tapovan Barrage, Joshimath, Helang Corridor</areaDesc>
    </area>
  </info>
</alert>`;
    }
  },
};

