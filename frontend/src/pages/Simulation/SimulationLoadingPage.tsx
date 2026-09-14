import React, { useEffect, useState } from 'react';
import { Link, useNavigate, useParams } from 'react-router-dom';
import { scenariosService } from '../../services/scenarios';
import { PipelineStage, RunStatus, SimulationStatusResponse } from '../../types/api';

const STAGES: { id: PipelineStage; label: string; description: string; estTime: string }[] = [
  {
    id: 'dem_fetch',
    label: 'DEM Acquisition & Terrain Conditioning',
    description: 'Fetching 30m topographic grid, conditioning hydraulic slopes and valley aspect.',
    estTime: '~0.8s',
  },
  {
    id: 'breach_estimation',
    label: 'Empirical Breach Hydrograph Fitting',
    description: 'Applying Froehlich (2008) & MacDonald regressions for peak discharge Qp and breach time tf.',
    estTime: '~0.2s',
  },
  {
    id: 'flood_routing',
    label: '2D Hydrodynamic Flood Routing',
    description: 'Simulating diffusive wave attenuation and corridor footprint polygons across time steps.',
    estTime: '~1.5s',
  },
  {
    id: 'summary_generation',
    label: 'Impact Extraction & Advisory Synthesis',
    description: 'Spatial ray-casting against downstream settlements, arrival times, and evacuation priorities.',
    estTime: '~0.4s',
  },
];

export const SimulationLoadingPage: React.FC = () => {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();

  const [statusData, setStatusData] = useState<SimulationStatusResponse | null>(null);
  const [errorMsg, setErrorMsg] = useState<string | null>(null);
  const [pollCount, setPollCount] = useState<number>(0);

  useEffect(() => {
    if (!id) return;

    let isMounted = true;

    const checkStatus = async () => {
      try {
        const data = await scenariosService.getSimulationStatus(id);
        if (!isMounted) return;

        setStatusData(data);
        setPollCount((prev) => prev + 1);

        if (data.status === 'succeeded') {
          // Brief pause so user sees 100% completion before transition
          setTimeout(() => {
            if (isMounted) {
              navigate(`/scenarios/${id}/results`);
            }
          }, 800);
        } else if (data.status === 'failed') {
          setErrorMsg(data.error_message || 'Simulation pipeline reported an unrecoverable failure.');
        }
      } catch (err: unknown) {
        if (isMounted) {
          const msg = err instanceof Error ? err.message : 'Error communicating with simulation orchestrator.';
          setErrorMsg(msg);
        }
      }
    };

    checkStatus();
    const interval = setInterval(checkStatus, 1200);

    return () => {
      isMounted = false;
      clearInterval(interval);
    };
  }, [id, navigate]);

  const currentStage = statusData?.current_stage;
  const runStatus: RunStatus = statusData?.status || 'pending';
  const progressPercent = statusData?.progress_percent || 10;
  const elapsed = statusData?.elapsed_seconds !== undefined ? statusData.elapsed_seconds : (pollCount * 1.2).toFixed(1);

  // Helper to determine stage state: 'completed' | 'active' | 'pending'
  const getStageState = (stageId: PipelineStage) => {
    if (runStatus === 'succeeded') return 'completed';
    if (!currentStage) return 'pending';

    const stageOrder: PipelineStage[] = [
      'dem_fetch',
      'breach_estimation',
      'flood_routing',
      'summary_generation',
    ];
    const currentIndex = stageOrder.indexOf(currentStage);
    const thisIndex = stageOrder.indexOf(stageId);

    if (thisIndex < currentIndex) return 'completed';
    if (thisIndex === currentIndex) return 'active';
    return 'pending';
  };

  const [isRetrying, setIsRetrying] = useState<boolean>(false);

  const handleRetrySimulation = async () => {
    if (!id) return;
    try {
      setIsRetrying(true);
      setErrorMsg(null);
      await scenariosService.triggerSimulation(id, 'full');
      setPollCount(0);
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : 'Unknown error';
      setErrorMsg(`Failed to re-trigger simulation: ${msg}`);
    } finally {
      setIsRetrying(false);
    }
  };

  return (
    <div className="flex-1 p-space-xl max-w-4xl mx-auto w-full flex flex-col gap-space-lg justify-center min-h-[calc(100vh-120px)]">
      {/* Progress Header Card */}
      <div className="bg-surface-container-lowest p-space-xl border border-outline/30 shadow-md flex flex-col gap-space-md">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-space-xs">
            <span className={`w-3 h-3 ${errorMsg ? 'bg-error' : 'bg-primary animate-ping'}`} />
            <span
              className={`font-mono text-xs font-bold uppercase tracking-wider ${
                errorMsg ? 'text-error' : 'text-primary'
              }`}
            >
              {errorMsg ? 'Simulation Fault Detected' : 'Simulation Pipeline Active'}
            </span>
          </div>

          <div className="font-mono text-xs text-secondary flex items-center gap-2">
            <span>ELAPSED:</span>
            <span className="font-bold text-on-surface bg-surface-container px-2 py-0.5 border border-outline/20">
              {elapsed}s
            </span>
          </div>
        </div>

        <div>
          <h1 className="text-2xl font-bold text-on-surface font-heading">
            {errorMsg ? 'Hydrodynamic Solver Halted' : 'Solving Inundation Hydrodynamics'}
          </h1>
          <p className="text-xs text-on-surface-variant mt-1">
            Running empirical breach regressions and 2D hydraulic wave routing for Scenario ID:{' '}
            <span className="font-mono text-primary font-bold">{id?.slice(0, 8)}...</span>
          </p>
        </div>

        {/* Progress Bar */}
        <div className="flex flex-col gap-1.5 mt-2">
          <div className="flex items-center justify-between font-mono text-xs">
            <span className="text-secondary font-semibold">OVERALL PIPELINE COMPLETION</span>
            <span className="text-primary font-bold text-sm">
              {errorMsg ? 'FAULT' : `${progressPercent}%`}
            </span>
          </div>
          <div className="w-full h-3 bg-surface-container border border-outline/20 overflow-hidden">
            <div
              className={`h-full transition-all duration-500 ease-out ${
                errorMsg ? 'bg-error w-full' : 'bg-primary'
              }`}
              style={{ width: errorMsg ? '100%' : `${progressPercent}%` }}
            />
          </div>
        </div>

        {/* Pipeline Stage Tracking Cards */}
        <div className="grid grid-cols-1 md:grid-cols-2 gap-space-md mt-2">
          {STAGES.map((stage) => {
            const state = getStageState(stage.id);
            const isErrorStage = statusData?.error_stage === stage.id;

            return (
              <div
                key={stage.id}
                className={`p-space-md border transition-colors flex items-start justify-between ${
                  isErrorStage
                    ? 'bg-error-container/40 border-error'
                    : state === 'completed'
                    ? 'bg-surface-container-low border-outline/20'
                    : state === 'active'
                    ? 'bg-primary-fixed/20 border-primary shadow-xs'
                    : 'bg-surface-container-lowest border-outline/10 opacity-60'
                }`}
              >
                <div className="flex items-start gap-space-sm">
                  <div className="mt-0.5">
                    {isErrorStage ? (
                      <span className="material-symbols-outlined text-base text-error">cancel</span>
                    ) : state === 'completed' ? (
                      <span className="material-symbols-outlined text-base text-emerald-600">
                        check_circle
                      </span>
                    ) : state === 'active' ? (
                      <span className="w-3.5 h-3.5 border-2 border-primary border-t-transparent animate-spin inline-block" />
                    ) : (
                      <span className="material-symbols-outlined text-base text-secondary">
                        radio_button_unchecked
                      </span>
                    )}
                  </div>

                  <div>
                    <div
                      className={`font-semibold text-xs ${
                        isErrorStage
                          ? 'text-error font-bold'
                          : state === 'active'
                          ? 'text-primary font-bold'
                          : state === 'completed'
                          ? 'text-on-surface'
                          : 'text-on-surface-variant'
                      }`}
                    >
                      {stage.label}
                    </div>
                    <div className="text-[11px] text-secondary mt-0.5">{stage.description}</div>
                  </div>
                </div>

                <div className="font-mono text-[10px] text-secondary">{stage.estTime}</div>
              </div>
            );
          })}
        </div>
      </div>

      {/* Failure & Remediation Screen */}
      {errorMsg && (
        <div className="p-space-lg bg-error-container/60 text-on-error-container border border-error shadow-md flex flex-col gap-3">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2 font-bold font-mono text-xs uppercase text-error">
              <span className="material-symbols-outlined text-base">report_problem</span>
              <span>Pipeline Stage Fault</span>
            </div>
            {statusData?.error_stage && (
              <span className="font-mono text-[10px] uppercase font-bold px-2 py-0.5 bg-error text-white">
                FAILED AT: {statusData.error_stage}
              </span>
            )}
          </div>

          <div className="p-3 bg-surface-container-lowest border border-outline/20 font-mono text-xs text-on-surface">
            {errorMsg}
          </div>

          <p className="text-[11px] text-on-surface-variant leading-relaxed">
            The hydrodynamic solver encountered an invalid numerical boundary or DEM void.
            You can modify the dam dimensions and simulation radius via the pre-filled configuration screen,
            or re-trigger the solve.
          </p>

          <div className="flex items-center gap-3 pt-1">
            <Link
              to={`/scenarios/new?editScenarioId=${id}`}
              className="px-3.5 py-2 bg-primary text-on-primary text-xs font-semibold hover:bg-primary-container transition-colors flex items-center gap-1.5 shadow-sm"
            >
              <span className="material-symbols-outlined text-sm">tune</span>
              <span>Edit Configuration</span>
            </Link>

            <button
              onClick={handleRetrySimulation}
              disabled={isRetrying}
              className="px-3.5 py-2 bg-surface-container border border-outline/30 text-xs font-semibold hover:bg-surface-container-high transition-colors flex items-center gap-1.5"
            >
              <span className="material-symbols-outlined text-sm">refresh</span>
              <span>{isRetrying ? 'Re-launching...' : 'Retry Simulation'}</span>
            </button>

            <Link
              to="/"
              className="px-3.5 py-2 bg-surface-container-low border border-outline/20 text-secondary text-xs font-semibold hover:text-on-surface transition-colors"
            >
              Return to Dashboard
            </Link>
          </div>
        </div>
      )}
    </div>
  );
};
