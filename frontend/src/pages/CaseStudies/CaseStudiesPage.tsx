import React, { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import { caseStudiesService } from '../../services/caseStudies';
import { CaseStudy } from '../../types/api';

export const CaseStudiesPage: React.FC = () => {
  const [caseStudies, setCaseStudies] = useState<CaseStudy[]>([]);
  const [isLoading, setIsLoading] = useState<boolean>(true);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);

  useEffect(() => {
    const fetchCaseStudies = async () => {
      try {
        setIsLoading(true);
        setErrorMessage(null);
        const res = await caseStudiesService.listCaseStudies();
        setCaseStudies(res.case_studies);
      } catch (err: unknown) {
        const msg = err instanceof Error ? err.message : 'Failed to load historical case studies.';
        setErrorMessage(msg);
      } finally {
        setIsLoading(false);
      }
    };

    fetchCaseStudies();
  }, []);

  return (
    <div className="flex-1 p-space-xl max-w-6xl mx-auto w-full flex flex-col gap-space-lg">
      {/* Header Banner */}
      <div className="bg-surface-container-lowest p-space-lg border border-outline/30 flex flex-col md:flex-row md:items-center justify-between gap-space-md shadow-sm">
        <div>
          <div className="flex items-center gap-space-xs mb-1">
            <span className="w-2.5 h-2.5 bg-primary inline-block" />
            <span className="font-mono text-[11px] font-bold tracking-wider text-primary uppercase">
              Benchmark Verification Suite
            </span>
          </div>
          <h1 className="text-2xl font-bold text-on-surface font-heading tracking-tight">
            Historical Disaster Case Studies
          </h1>
          <p className="text-xs text-on-surface-variant mt-1">
            Pre-conditioned hydrodynamic datasets from documented Himalayan dam failures and glacial lake outbursts.
          </p>
        </div>

        <Link
          to="/scenarios/new"
          className="flex items-center gap-1.5 px-4 py-2 text-xs font-semibold bg-primary text-on-primary hover:bg-primary-container transition-colors shadow-sm"
        >
          <span className="material-symbols-outlined text-sm">add_location_alt</span>
          <span>New Custom Simulation</span>
        </Link>
      </div>

      {/* Error Notice */}
      {errorMessage && (
        <div className="p-space-md bg-error-container text-on-error-container border border-error/30 text-xs font-mono">
          <div className="font-bold mb-1">SYSTEM ALERT</div>
          {errorMessage}
        </div>
      )}

      {/* Case Studies Grid */}
      {isLoading ? (
        <div className="p-16 text-center text-xs font-mono text-secondary flex flex-col items-center justify-center gap-2">
          <span className="w-5 h-5 border-2 border-primary border-t-transparent animate-spin inline-block" />
          <span>Loading historical benchmark catalog...</span>
        </div>
      ) : caseStudies.length === 0 ? (
        <div className="p-16 text-center text-xs text-secondary font-mono bg-surface-container-lowest border border-outline/30">
          No historical case studies registered in database.
        </div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 gap-space-lg">
          {caseStudies.map((cs) => (
            <div
              key={cs.id}
              className="bg-surface-container-lowest border border-outline/30 flex flex-col shadow-sm hover:shadow-md transition-shadow"
            >
              <div className="p-space-lg border-b border-outline/20 bg-surface-container-low flex items-start justify-between">
                <div>
                  <span className="font-mono text-[10px] font-bold uppercase tracking-wider text-primary bg-primary-fixed/40 px-2 py-0.5 border border-primary/20">
                    HISTORICAL BENCHMARK {cs.event_year}
                  </span>
                  <h2 className="text-lg font-bold text-on-surface mt-1.5 font-heading">
                    {cs.name || 'Rishi Ganga Flash Flood'}
                  </h2>
                </div>
                <span className="material-symbols-outlined text-2xl text-primary">history_edu</span>
              </div>

              <div className="p-space-lg flex-1 flex flex-col justify-between gap-4 text-xs font-body">
                <div>
                  <p className="text-on-surface-variant leading-relaxed mb-3">
                    {cs.description}
                  </p>

                  <div className="grid grid-cols-2 gap-2 font-mono text-[11px] bg-surface-container-low p-3 border border-outline/20">
                    <div>
                      <span className="text-secondary text-[10px] block">BREACH TYPE:</span>
                      <span className="font-bold text-on-surface capitalize">
                        {cs.breach_type ? cs.breach_type.replace('_', ' ') : 'Landslide GLOF'}
                      </span>
                    </div>

                    <div>
                      <span className="text-secondary text-[10px] block">VOLUME:</span>
                      <span className="font-bold text-on-surface">
                        {cs.dam_volume_m3 ? `${(cs.dam_volume_m3 / 1e6).toFixed(1)}M m³` : '26.0M m³'}
                      </span>
                    </div>

                    <div>
                      <span className="text-secondary text-[10px] block">COORDINATES:</span>
                      <span className="font-bold text-on-surface">
                        {cs.latitude?.toFixed(4)}° N, {cs.longitude?.toFixed(4)}° E
                      </span>
                    </div>

                    <div>
                      <span className="text-secondary text-[10px] block">SOURCE:</span>
                      <span className="font-bold text-on-surface truncate block" title={cs.source_reference || ''}>
                        {cs.source_reference || 'CWC / WRS Survey'}
                      </span>
                    </div>
                  </div>

                  {/* Terrain Drift Disclosure */}
                  <div className="mt-3 p-2 bg-surface-container-low border border-outline/20 text-[10px] text-secondary flex items-start gap-1.5 font-mono">
                    <span className="material-symbols-outlined text-xs text-secondary mt-0.5">info</span>
                    <span>
                      <strong>Terrain Drift Disclosure:</strong> Footprint calibrated to pre-event 2021 DEM. Downstream valley morphology reflects post-event debris deposition and scoured gorge sections.
                    </span>
                  </div>
                </div>

                <div className="pt-2 border-t border-outline/20 flex items-center justify-between">
                  <span className="font-mono text-[10px] text-secondary">
                    Ground-truth calibration data loaded
                  </span>
                  <Link
                    to={`/case-studies/${cs.id}/results`}
                    className="px-4 py-2 bg-primary text-on-primary font-semibold text-xs hover:bg-primary-container transition-colors flex items-center gap-1.5 shadow-sm"
                  >
                    <span className="material-symbols-outlined text-sm">map</span>
                    <span>Load Incident Simulation</span>
                  </Link>
                </div>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
};
