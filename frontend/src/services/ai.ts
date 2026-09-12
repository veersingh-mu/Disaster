/**
 * AI Tactical Evacuation Briefing service.
 * Connects to the secure server-side endpoint POST /scenarios/:id/ai-briefing.
 * Note: API keys are strictly kept server-side and never exposed in client code.
 */

import { apiFetch } from './api';

export interface SettlementTimelineItem {
  settlement_id: string;
  name: string;
  district: string;
  state: string;
  arrival_time_minutes: number;
  estimated_depth_m: number | null;
  evacuation_priority: 'IMMEDIATE' | 'HIGH' | 'STANDBY' | 'MONITOR' | string;
  recommended_action: string;
}

export interface AIBriefingResponse {
  scenario_id: string;
  headline: string;
  evacuation_urgency: 'IMMEDIATE' | 'HIGH' | 'MODERATE' | 'ADVISORY' | string;
  executive_summary: string;
  settlement_timeline: SettlementTimelineItem[];
  resource_staging_advisory: string[];
  public_advisory_bulletin: string;
  model_used: string;
  is_fallback: boolean;
  generated_at: string;
}

export interface AIBriefingRequest {
  focus_area?: string;
  urgency_level?: string;
  custom_instructions?: string;
}

export const aiService = {
  generateBriefing: async (
    id: string,
    payload?: AIBriefingRequest,
    isCaseStudy = false
  ): Promise<AIBriefingResponse> => {
    const endpoint = isCaseStudy
      ? `/case-studies/${id}/ai-briefing`
      : `/scenarios/${id}/ai-briefing`;
    return apiFetch<AIBriefingResponse>(endpoint, {
      method: 'POST',
      body: payload ? JSON.stringify(payload) : JSON.stringify({}),
    });
  },
};
