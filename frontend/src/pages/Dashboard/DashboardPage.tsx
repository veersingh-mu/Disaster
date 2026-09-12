import React, { useEffect, useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { scenariosService } from '../../services/scenarios';
import { Scenario } from '../../types/api';

export const DashboardPage: React.FC = () => {
  const navigate = useNavigate();
  const [scenarios, setScenarios] = useState<Scenario[]>([]);
  const [isLoading, setIsLoading] = useState<boolean>(true);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const [actionLoadingId, setActionLoadingId] = useState<string | null>(null);

  const fetchScenarios = async () => {
    try {
      setIsLoading(true);
      setErrorMessage(null);
      const res = await scenariosService.listScenarios();
      setScenarios(res.scenarios);
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : 'Failed to load scenarios';
      setErrorMessage(msg);
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    fetchScenarios();
  }, []);

  const handleRunSimulation = async (scenario: Scenario) => {
    try {
      setActionLoadingId(scenario.id);
      await scenariosService.triggerSimulation(scenario.id, 'full');
      navigate(`/scenarios/${scenario.id}/simulating`);
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : 'Unknown error';
      alert(`Simulation failed to start: ${msg}`);
      setActionLoadingId(null);
    }
  };

  const handleDelete = async (id: string, name: string) => {
    if (!window.confirm(`Are you sure you want to delete scenario "${name}"?`)) {
      return;
    }
    try {
      await scenariosService.deleteScenario(id);
      setScenarios((prev) => prev.filter((s) => s.id !== id));
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : 'Unknown error';
      alert(`Failed to delete scenario: ${msg}`);
    }
  };

  // Metrics computation
  const totalScenarios = scenarios.length;
  const completedRuns = scenarios.filter((s) => s.latest_run_status === 'succeeded').length;
  const activeRuns = scenarios.filter(
    (s) => s.latest_run_status === 'running' || s.latest_run_status === 'pending'
  ).length;

  return (
    <div className="flex-1 p-space-xl max-w-7xl mx-auto w-full flex flex-col gap-space-lg">
      {/* Header Banner */}
      <div className="bg-surface-container-lowest p-space-lg border border-outline/30 flex flex-col md:flex-row md:items-center justify-between gap-space-md shadow-sm">
        <div>
          <div className="flex items-center gap-space-xs mb-1">
            <span className="w-2.5 h-2.5 bg-primary inline-block" />
            <span className="font-mono text-[11px] font-bold tracking-wider text-primary uppercase">
              Operational Command Center
            </span>
          </div>
          <h1 className="text-2xl font-bold text-on-surface font-heading tracking-tight">
            Dam & Glacial Lake Breach Scenarios
          </h1>
          <p className="text-xs text-on-surface-variant mt-1">
            Rapid physics-based inundation hydrograph routing and downstream settlement impact forecasting.
          </p>
        </div>

        <div className="flex items-center gap-2">
          <Link
            to="/case-studies"
            className="flex items-center gap-1.5 px-3 py-2 text-xs font-semibold bg-surface-container border border-outline/30 text-on-surface hover:bg-surface-container-high transition-colors"
          >
            <span className="material-symbols-outlined text-sm">history_edu</span>
            <span>Historical Benchmarks</span>
          </Link>

          <Link
            to="/scenarios/new"
            className="flex items-center gap-1.5 px-4 py-2 text-xs font-semibold bg-primary text-on-primary hover:bg-primary-container transition-colors shadow-sm"
          >
            <span className="material-symbols-outlined text-sm">add_location_alt</span>
            <span>New Simulation</span>
          </Link>
        </div>
      </div>

      {/* Metrics Row */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-space-md">
        <div className="bg-surface-container-lowest p-space-md border border-outline/30 flex flex-col shadow-sm">
          <span className="font-mono text-[11px] text-on-surface-variant uppercase tracking-wider font-semibold">
            Monitored Sites
          </span>
          <span className="font-mono text-2xl font-bold text-primary mt-1">{totalScenarios}</span>
          <span className="text-[11px] text-secondary mt-1">Configured breach locations</span>
        </div>

        <div className="bg-surface-container-lowest p-space-md border border-outline/30 flex flex-col shadow-sm">
          <span className="font-mono text-[11px] text-on-surface-variant uppercase tracking-wider font-semibold">
            Completed Solves
          </span>
          <span className="font-mono text-2xl font-bold text-emerald-700 mt-1">{completedRuns}</span>
          <span className="text-[11px] text-secondary mt-1">Full 2D hydrodynamic routes</span>
        </div>

        <div className="bg-surface-container-lowest p-space-md border border-outline/30 flex flex-col shadow-sm">
          <span className="font-mono text-[11px] text-on-surface-variant uppercase tracking-wider font-semibold">
            Pipeline Jobs In Flight
          </span>
          <span className="font-mono text-2xl font-bold text-amber-600 mt-1">{activeRuns}</span>
          <span className="text-[11px] text-secondary mt-1">Active worker computations</span>
        </div>

        <div className="bg-surface-container-lowest p-space-md border border-outline/30 flex flex-col shadow-sm">
          <span className="font-mono text-[11px] text-on-surface-variant uppercase tracking-wider font-semibold">
            DEM Coverage Baseline
          </span>
          <span className="font-mono text-2xl font-bold text-primary mt-1">30m</span>
          <span className="text-[11px] text-secondary mt-1">SRTM / HydroSHEDS conditioned</span>
        </div>
      </div>

      {/* Error Notice */}
      {errorMessage && (
        <div className="p-space-md bg-error-container text-on-error-container border border-error/30 text-xs font-mono">
          <div className="font-bold mb-1">SYSTEM ALERT</div>
          {errorMessage}
        </div>
      )}

      {/* Scenarios Table */}
      <div className="bg-surface-container-lowest border border-outline/30 shadow-sm flex flex-col">
        <div className="p-space-md bg-surface-container-low border-b border-outline/20 flex items-center justify-between">
          <div className="flex items-center gap-space-xs">
            <span className="material-symbols-outlined text-base text-primary">analytics</span>
            <h2 className="font-semibold text-sm tracking-tight text-on-surface">
              Configured Scenario Registry
            </h2>
          </div>
          <button
            onClick={fetchScenarios}
            className="flex items-center gap-1 text-[11px] text-secondary hover:text-primary transition-colors font-mono"
          >
            <span className="material-symbols-outlined text-sm">refresh</span>
            <span>Refresh Table</span>
          </button>
        </div>

        {isLoading ? (
          <div className="p-12 text-center text-xs font-mono text-secondary flex flex-col items-center justify-center gap-2">
            <span className="w-5 h-5 border-2 border-primary border-t-transparent animate-spin inline-block" />
            <span>Retrieving incident catalog from database...</span>
          </div>
        ) : scenarios.length === 0 ? (
          <div className="p-16 text-center flex flex-col items-center justify-center gap-3">
            <span className="material-symbols-outlined text-4xl text-outline-variant">landscape</span>
            <div className="font-semibold text-base text-on-surface">No simulation scenarios yet</div>
            <p className="text-xs text-on-surface-variant max-w-md">
              Initialize a scenario by selecting a Himalayan dam or moraine-dammed glacial lake site,
              or load our pre-validated historical benchmark.
            </p>
            <div className="flex items-center gap-2 mt-2">
              <Link
                to="/scenarios/new"
                className="px-4 py-2 text-xs font-semibold bg-primary text-on-primary hover:bg-primary-container transition-colors"
              >
                Create Scenario
              </Link>
              <Link
                to="/case-studies"
                className="px-4 py-2 text-xs font-semibold bg-surface-container border border-outline/30 hover:bg-surface-container-high transition-colors"
              >
                View Benchmarks
              </Link>
            </div>
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-left border-collapse text-xs">
              <thead>
                <tr className="border-b border-outline/20 bg-surface-container-lowest font-mono text-[11px] text-on-surface-variant uppercase tracking-wider">
                  <th className="py-2.5 px-4 font-semibold">Scenario Identifier</th>
                  <th className="py-2.5 px-4 font-semibold">Breach Mechanics</th>
                  <th className="py-2.5 px-4 font-semibold">Coordinates (Lat, Lon)</th>
                  <th className="py-2.5 px-4 font-semibold">Dam Height & Vol</th>
                  <th className="py-2.5 px-4 font-semibold">Simulation Status</th>
                  <th className="py-2.5 px-4 font-semibold text-right">Actions</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-outline/10 font-body">
                {scenarios.map((sc) => {
                  const status = sc.latest_run_status || 'not_run';
                  return (
                    <tr key={sc.id} className="hover:bg-surface-container-low transition-colors">
                      <td className="py-3 px-4">
                        <div className="font-semibold text-on-surface">{sc.name}</div>
                        <div className="font-mono text-[10px] text-secondary">ID: {sc.id.slice(0, 8)}...</div>
                      </td>

                      <td className="py-3 px-4">
                        <span
                          className={`inline-block px-2 py-0.5 text-[10px] font-mono font-bold uppercase tracking-wider ${
                            sc.breach_type === 'landslide_glof'
                              ? 'bg-amber-100 text-amber-900 border border-amber-300'
                              : 'bg-blue-100 text-blue-900 border border-blue-300'
                          }`}
                        >
                          {sc.breach_type === 'landslide_glof' ? 'GLOF Overtop' : 'Structural'}
                        </span>
                      </td>

                      <td className="py-3 px-4 font-mono text-[11px] text-on-surface">
                        {sc.latitude.toFixed(4)}° N, {sc.longitude.toFixed(4)}° E
                      </td>

                      <td className="py-3 px-4 font-mono text-[11px]">
                        <div>H: {sc.dam_height_m}m</div>
                        <div className="text-secondary">V: {(sc.dam_volume_m3 / 1e6).toFixed(1)}M m³</div>
                      </td>

                      <td className="py-3 px-4">
                        <span
                          className={`inline-flex items-center gap-1 px-2 py-0.5 text-[10px] font-mono font-bold uppercase tracking-wider ${
                            status === 'succeeded'
                              ? 'bg-emerald-100 text-emerald-800 border border-emerald-300'
                              : status === 'running' || status === 'pending'
                              ? 'bg-amber-100 text-amber-800 border border-amber-300 animate-pulse'
                              : status === 'failed'
                              ? 'bg-rose-100 text-rose-800 border border-rose-300'
                              : 'bg-slate-100 text-slate-700 border border-slate-300'
                          }`}
                        >
                          <span
                            className={`w-1.5 h-1.5 rounded-full ${
                              status === 'succeeded'
                                ? 'bg-emerald-600'
                                : status === 'running' || status === 'pending'
                                ? 'bg-amber-500'
                                : status === 'failed'
                                ? 'bg-rose-600'
                                : 'bg-slate-400'
                            }`}
                          />
                          {status}
                        </span>
                      </td>

                      <td className="py-3 px-4 text-right">
                        <div className="flex items-center justify-end gap-1.5">
                          {status === 'succeeded' ? (
                            <Link
                              to={`/scenarios/${sc.id}/results`}
                              className="px-2.5 py-1 bg-primary text-on-primary text-[11px] font-medium hover:bg-primary-container transition-colors flex items-center gap-1"
                            >
                              <span className="material-symbols-outlined text-xs">map</span>
                              <span>Inundation Map</span>
                            </Link>
                          ) : (
                            <button
                              onClick={() => handleRunSimulation(sc)}
                              disabled={actionLoadingId === sc.id}
                              className="px-2.5 py-1 bg-surface-container border border-outline/30 text-on-surface text-[11px] font-medium hover:bg-surface-container-high transition-colors flex items-center gap-1"
                            >
                              <span className="material-symbols-outlined text-xs">play_arrow</span>
                              <span>{actionLoadingId === sc.id ? 'Starting...' : 'Run Simulation'}</span>
                            </button>
                          )}

                          <button
                            onClick={() => handleDelete(sc.id, sc.name)}
                            className="p-1 text-outline hover:text-error hover:bg-error-container/30 transition-colors"
                            title="Delete scenario"
                          >
                            <span className="material-symbols-outlined text-sm">delete</span>
                          </button>
                        </div>
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </div>
  );
};
