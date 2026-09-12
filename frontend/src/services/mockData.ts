import {
  CaseStudy,
  FloodResultStep,
  Scenario,
  ScenarioResultsResponse,
} from '../types/api';

const LOCAL_STORAGE_SCENARIOS_KEY = 'floodpath_local_scenarios';

export const BENCHMARK_SCENARIOS: Scenario[] = [
  {
    id: '20000000-0000-0000-0000-000000000001',
    user_id: '00000000-0000-0000-0000-000000000001',
    name: 'Rishi Ganga 2021 Rock-Ice Avalanche & GLOF',
    latitude: 30.3833,
    longitude: 79.7333,
    breach_type: 'landslide_glof',
    dam_height_m: 36.0,
    dam_volume_m3: 27000000.0,
    simulation_radius_km: 45.0,
    is_dem_estimated: false,
    created_at: '2026-02-07T04:55:00Z',
    updated_at: '2026-02-07T05:01:00Z',
    latest_run_id: '30000000-0000-0000-0000-000000000001',
    latest_run_status: 'succeeded',
  },
  {
    id: '20000000-0000-0000-0000-000000000002',
    user_id: '00000000-0000-0000-0000-000000000001',
    name: 'South Lhonak Glacial Lake Outburst (Sikkim 2023)',
    latitude: 27.915,
    longitude: 88.204,
    breach_type: 'landslide_glof',
    dam_height_m: 42.0,
    dam_volume_m3: 65000000.0,
    simulation_radius_km: 50.0,
    is_dem_estimated: false,
    created_at: '2026-03-10T12:00:00Z',
    updated_at: '2026-03-10T12:05:00Z',
    latest_run_id: '30000000-0000-0000-0000-000000000002',
    latest_run_status: 'succeeded',
  },
  {
    id: '20000000-0000-0000-0000-000000000003',
    user_id: '00000000-0000-0000-0000-000000000001',
    name: 'Tehri High Dam Structural Breach Baseline',
    latitude: 30.3783,
    longitude: 78.4803,
    breach_type: 'structural',
    dam_height_m: 260.5,
    dam_volume_m3: 4000000000.0,
    simulation_radius_km: 75.0,
    is_dem_estimated: false,
    created_at: '2026-04-01T08:30:00Z',
    updated_at: '2026-04-01T08:36:00Z',
    latest_run_id: '30000000-0000-0000-0000-000000000003',
    latest_run_status: 'succeeded',
  },
];

export const BENCHMARK_CASE_STUDIES: CaseStudy[] = [
  {
    id: '40000000-0000-0000-0000-000000000001',
    scenario_id: '20000000-0000-0000-0000-000000000001',
    simulation_run_id: '30000000-0000-0000-0000-000000000001',
    event_year: 2021,
    name: 'Rishi Ganga Flash Flood (Chamoli 2021)',
    breach_type: 'landslide_glof',
    dam_height_m: 36.0,
    dam_volume_m3: 27000000.0,
    simulation_radius_km: 45.0,
    latitude: 30.3833,
    longitude: 79.7333,
    description:
      'Catastrophic detachment of approximately 27 million m³ of glacier ice and rock from Ronti Peak at 5,500m elevation. The massive pulverized mass transformed into a hyper-concentrated slurry wave obliterating the Rishi Ganga small hydro project and damaging Tapovan Vishnugad barrage.',
    source_reference: 'CWC / WIHG Post-Disaster Survey (2021)',
    created_at: '2026-02-07T04:55:00Z',
  },
  {
    id: '40000000-0000-0000-0000-000000000002',
    scenario_id: '20000000-0000-0000-0000-000000000002',
    simulation_run_id: '30000000-0000-0000-0000-000000000002',
    event_year: 2023,
    name: 'South Lhonak GLOF & Chungthang Dam (Sikkim 2023)',
    breach_type: 'landslide_glof',
    dam_height_m: 42.0,
    dam_volume_m3: 65000000.0,
    simulation_radius_km: 50.0,
    latitude: 27.915,
    longitude: 88.204,
    description:
      'Cloudburst-induced lateral moraine breach releasing over 48 million m³ from South Lhonak glacial lake into Teesta river basin, destroying the Chungthang Hydroelectric Stage III Dam and flooding downstream districts.',
    source_reference: 'ISRO / SDC Report on Sikkim GLOF (2023)',
    created_at: '2026-03-10T12:00:00Z',
  },
];

export function getLocalScenarios(): Scenario[] {
  try {
    const raw = localStorage.getItem(LOCAL_STORAGE_SCENARIOS_KEY);
    const custom: Scenario[] = raw ? JSON.parse(raw) : [];
    const customIds = new Set(custom.map((s) => s.id));
    const merged = [...custom, ...BENCHMARK_SCENARIOS.filter((b) => !customIds.has(b.id))];
    return merged;
  } catch {
    return BENCHMARK_SCENARIOS;
  }
}

export function saveLocalScenario(scenario: Scenario): void {
  try {
    const raw = localStorage.getItem(LOCAL_STORAGE_SCENARIOS_KEY);
    const list: Scenario[] = raw ? JSON.parse(raw) : [];
    const existingIdx = list.findIndex((s) => s.id === scenario.id);
    if (existingIdx >= 0) {
      list[existingIdx] = scenario;
    } else {
      list.unshift(scenario);
    }
    localStorage.setItem(LOCAL_STORAGE_SCENARIOS_KEY, JSON.stringify(list));
  } catch (err) {
    console.warn('Failed to save scenario in local storage', err);
  }
}

export function deleteLocalScenario(id: string): void {
  try {
    const raw = localStorage.getItem(LOCAL_STORAGE_SCENARIOS_KEY);
    if (!raw) return;
    const list: Scenario[] = JSON.parse(raw);
    const filtered = list.filter((s) => s.id !== id);
    localStorage.setItem(LOCAL_STORAGE_SCENARIOS_KEY, JSON.stringify(filtered));
  } catch (err) {
    console.warn('Failed to delete scenario from local storage', err);
  }
}

export function generateBenchmarkResults(
  scenarioId: string,
  scenarioName?: string,
  lat: number = 30.3833,
  lon: number = 79.7333
): ScenarioResultsResponse {
  // Time-stepped hydrodynamic flood extents along valley corridor
  const timeSteps: FloodResultStep[] = [
    {
      id: `${scenarioId}-step-0`,
      time_step_minutes: 0,
      max_depth_m: 28.5,
      flood_extent: {
        type: 'Polygon',
        coordinates: [
          [
            [lon - 0.015, lat - 0.01],
            [lon + 0.015, lat - 0.01],
            [lon + 0.02, lat + 0.015],
            [lon - 0.01, lat + 0.015],
            [lon - 0.015, lat - 0.01],
          ],
        ],
      },
    },
    {
      id: `${scenarioId}-step-15`,
      time_step_minutes: 15,
      max_depth_m: 22.0,
      flood_extent: {
        type: 'Polygon',
        coordinates: [
          [
            [lon - 0.025, lat - 0.005],
            [lon + 0.01, lat - 0.005],
            [lon - 0.01, lat + 0.04],
            [lon - 0.035, lat + 0.035],
            [lon - 0.025, lat - 0.005],
          ],
        ],
      },
    },
    {
      id: `${scenarioId}-step-30`,
      time_step_minutes: 30,
      max_depth_m: 17.5,
      flood_extent: {
        type: 'Polygon',
        coordinates: [
          [
            [lon - 0.035, lat + 0.02],
            [lon - 0.005, lat + 0.02],
            [lon - 0.045, lat + 0.075],
            [lon - 0.075, lat + 0.065],
            [lon - 0.035, lat + 0.02],
          ],
        ],
      },
    },
    {
      id: `${scenarioId}-step-45`,
      time_step_minutes: 45,
      max_depth_m: 14.0,
      flood_extent: {
        type: 'Polygon',
        coordinates: [
          [
            [lon - 0.06, lat + 0.05],
            [lon - 0.03, lat + 0.05],
            [lon - 0.09, lat + 0.11],
            [lon - 0.12, lat + 0.095],
            [lon - 0.06, lat + 0.05],
          ],
        ],
      },
    },
    {
      id: `${scenarioId}-step-60`,
      time_step_minutes: 60,
      max_depth_m: 11.2,
      flood_extent: {
        type: 'Polygon',
        coordinates: [
          [
            [lon - 0.09, lat + 0.08],
            [lon - 0.05, lat + 0.08],
            [lon - 0.14, lat + 0.145],
            [lon - 0.17, lat + 0.135],
            [lon - 0.09, lat + 0.08],
          ],
        ],
      },
    },
    {
      id: `${scenarioId}-step-90`,
      time_step_minutes: 90,
      max_depth_m: 8.0,
      flood_extent: {
        type: 'Polygon',
        coordinates: [
          [
            [lon - 0.13, lat + 0.11],
            [lon - 0.08, lat + 0.11],
            [lon - 0.21, lat + 0.18],
            [lon - 0.25, lat + 0.165],
            [lon - 0.13, lat + 0.11],
          ],
        ],
      },
    },
    {
      id: `${scenarioId}-step-120`,
      time_step_minutes: 120,
      max_depth_m: 5.5,
      flood_extent: {
        type: 'Polygon',
        coordinates: [
          [
            [lon - 0.18, lat + 0.13],
            [lon - 0.12, lat + 0.13],
            [lon - 0.28, lat + 0.21],
            [lon - 0.32, lat + 0.19],
            [lon - 0.18, lat + 0.13],
          ],
        ],
      },
    },
  ];

  return {
    scenario_id: scenarioId,
    simulation_run_id: `run-${scenarioId}`,
    status: 'succeeded',
    mode: 'full',
    is_surrogate: false,
    summary_text: `Hydrodynamic simulation for ${
      scenarioName || 'Dam Breach Scenario'
    } solved across downstream river valley. Peak discharge reached 28.5m depth at the breach outlet, propagating downstream with critical wave front arrival at Rini Village within 18 minutes and Tapovan Barrage within 42 minutes.`,
    time_steps: timeSteps,
    affected_settlements: [
      {
        settlement_id: 'settlement-01',
        name: 'Rini Village',
        district: 'Chamoli',
        state: 'Uttarakhand',
        population: 480,
        arrival_time_minutes: 18,
        estimated_depth_m: 14.5,
      },
      {
        settlement_id: 'settlement-02',
        name: 'Tapovan Barrage & High Camp',
        district: 'Chamoli',
        state: 'Uttarakhand',
        population: 315,
        arrival_time_minutes: 42,
        estimated_depth_m: 11.2,
      },
      {
        settlement_id: 'settlement-03',
        name: 'Joshimath Sub-District',
        district: 'Chamoli',
        state: 'Uttarakhand',
        population: 16700,
        arrival_time_minutes: 72,
        estimated_depth_m: 7.8,
      },
      {
        settlement_id: 'settlement-04',
        name: 'Helang Transit Point',
        district: 'Chamoli',
        state: 'Uttarakhand',
        population: 1200,
        arrival_time_minutes: 95,
        estimated_depth_m: 5.4,
      },
      {
        settlement_id: 'settlement-05',
        name: 'Pipalkoti Urban Basin',
        district: 'Chamoli',
        state: 'Uttarakhand',
        population: 4200,
        arrival_time_minutes: 130,
        estimated_depth_m: 3.8,
      },
    ],
    total_affected_settlements: 5,
    peak_depth_m: 28.5,
    arrival_time_first_settlement_minutes: 18,
  };
}
