import { apiFetch } from './api';
import { CaseStudyListResponse, ScenarioResultsResponse } from '../types/api';

export const caseStudiesService = {
  async listCaseStudies(): Promise<CaseStudyListResponse> {
    return apiFetch<CaseStudyListResponse>('/case-studies');
  },

  async getCaseStudyResults(id: string): Promise<ScenarioResultsResponse> {
    return apiFetch<ScenarioResultsResponse>(`/case-studies/${id}/results`);
  },
};
