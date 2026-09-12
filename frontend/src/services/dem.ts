import { apiFetch } from './api';
import { DEMPreviewResponse } from '../types/api';

export const demService = {
  async previewDEM(
    latitude: number,
    longitude: number,
    simulationRadiusKm: number = 25.0
  ): Promise<DEMPreviewResponse> {
    return apiFetch<DEMPreviewResponse>(
      `/dem/preview?latitude=${latitude}&longitude=${longitude}&simulation_radius_km=${simulationRadiusKm}`
    );
  },
};
