import { apiFetch, ApiFetchError } from './api';
import { CaseStudyListResponse, ScenarioResultsResponse } from '../types/api';
import { BENCHMARK_CASE_STUDIES, generateBenchmarkResults } from './mockData';

export const caseStudiesService = {
  async listCaseStudies(): Promise<CaseStudyListResponse> {
    try {
      return await apiFetch<CaseStudyListResponse>('/case-studies');
    } catch (err: unknown) {
      if ((err as ApiFetchError)?.isNetworkError) {
        return {
          case_studies: BENCHMARK_CASE_STUDIES,
          total: BENCHMARK_CASE_STUDIES.length,
        };
      }
      throw err;
    }
  },

  async getCaseStudyResults(id: string): Promise<ScenarioResultsResponse> {
    try {
      return await apiFetch<ScenarioResultsResponse>(`/case-studies/${id}/results`);
    } catch (err: unknown) {
      if ((err as ApiFetchError)?.isNetworkError) {
        const found = BENCHMARK_CASE_STUDIES.find((cs) => cs.id === id);
        return generateBenchmarkResults(
          id,
          found?.name || 'Historical Benchmark Case Study',
          found?.latitude || 30.3833,
          found?.longitude || 79.7333
        );
      }
      throw err;
    }
  },
};

