import React, { useState, useEffect, useCallback } from 'react';
import { aiService, AIBriefingResponse } from '../services/ai';

interface AIBriefingCardProps {
  scenarioId: string;
  isCaseStudy?: boolean;
  autoFetch?: boolean;
}

export const AIBriefingCard: React.FC<AIBriefingCardProps> = ({
  scenarioId,
  isCaseStudy = false,
  autoFetch = true,
}) => {
  const [briefing, setBriefing] = useState<AIBriefingResponse | null>(null);
  const [loading, setLoading] = useState<boolean>(false);
  const [error, setError] = useState<string | null>(null);
  const [copied, setCopied] = useState<boolean>(false);

  const fetchBriefing = useCallback(async () => {
    if (!scenarioId) return;
    try {
      setLoading(true);
      setError(null);
      const data = await aiService.generateBriefing(scenarioId, undefined, isCaseStudy);
      setBriefing(data);
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : 'Unable to generate AI evacuation briefing.';
      setError(msg);
    } finally {
      setLoading(false);
    }
  }, [scenarioId, isCaseStudy]);

  useEffect(() => {
    if (autoFetch) {
      fetchBriefing();
    }
  }, [autoFetch, fetchBriefing]);

  const handleCopyOrder = () => {
    if (!briefing) return;
    const textToCopy = `=== TACTICAL DISASTER EVACUATION BRIEFING ===
HEADLINE: ${briefing.headline}
URGENCY: ${briefing.evacuation_urgency}
GENERATED: ${new Date(briefing.generated_at).toLocaleString()}
MODEL: ${briefing.model_used}

EXECUTIVE SUMMARY:
${briefing.executive_summary}

VILLAGE EVACUATION TIMELINE:
${briefing.settlement_timeline
  .map(
    (s) =>
      `• [${s.evacuation_priority}] ${s.name} (${s.district}, ${s.state}) - T+${s.arrival_time_minutes} min | Est. Depth: ${s.estimated_depth_m ?? 'N/A'}m\n  Action: ${s.recommended_action}`
  )
  .join('\n')}

TACTICAL RESOURCE STAGING:
${briefing.resource_staging_advisory.map((r, i) => `${i + 1}. ${r}`).join('\n')}

PUBLIC BROADCAST BULLETIN:
${briefing.public_advisory_bulletin}
=============================================`;

    navigator.clipboard.writeText(textToCopy);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  const getUrgencyBadge = (urgency: string) => {
    switch (urgency.toUpperCase()) {
      case 'IMMEDIATE':
        return 'bg-red-900/40 text-red-300 border-red-500/50';
      case 'HIGH':
        return 'bg-amber-900/40 text-amber-300 border-amber-500/50';
      case 'MODERATE':
        return 'bg-yellow-900/40 text-yellow-300 border-yellow-500/50';
      default:
        return 'bg-slate-800 text-slate-300 border-slate-700';
    }
  };

  const getPriorityBadge = (priority: string) => {
    switch (priority.toUpperCase()) {
      case 'IMMEDIATE':
        return 'bg-red-500/20 text-red-400 border-red-500/30';
      case 'HIGH':
        return 'bg-amber-500/20 text-amber-400 border-amber-500/30';
      case 'STANDBY':
        return 'bg-blue-500/20 text-blue-400 border-blue-500/30';
      default:
        return 'bg-slate-800 text-slate-400 border-slate-700';
    }
  };

  return (
    <div className="bg-slate-900 border border-slate-700 rounded-lg p-5 shadow-lg relative overflow-hidden">
      {/* Card Header */}
      <div className="flex flex-wrap items-center justify-between gap-3 border-b border-slate-800 pb-4 mb-4">
        <div className="flex items-center gap-2.5">
          <div className="w-8 h-8 rounded-md bg-indigo-500/20 border border-indigo-500/40 flex items-center justify-center text-indigo-400">
            <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 10V3L4 14h7v7l9-11h-7z" />
            </svg>
          </div>
          <div>
            <div className="flex items-center gap-2">
              <h3 className="text-sm font-semibold text-white tracking-wide uppercase">
                AI Tactical Evacuation Briefing
              </h3>
              {briefing && (
                <span
                  className={`text-[10px] font-mono px-2 py-0.5 rounded border ${getUrgencyBadge(
                    briefing.evacuation_urgency
                  )}`}
                >
                  {briefing.evacuation_urgency}
                </span>
              )}
            </div>
            <p className="text-xs text-slate-400">
              NDMA / SEOC Automated Tactical Intelligence Order
            </p>
          </div>
        </div>

        <div className="flex items-center gap-2">
          {briefing && (
            <button
              onClick={handleCopyOrder}
              disabled={loading}
              className="text-xs font-mono px-3 py-1.5 rounded bg-slate-800 hover:bg-slate-700 text-slate-200 border border-slate-600 transition flex items-center gap-1.5"
              title="Copy formatted dispatch order"
            >
              {copied ? (
                <>
                  <svg className="w-3.5 h-3.5 text-emerald-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
                  </svg>
                  <span>Copied</span>
                </>
              ) : (
                <>
                  <svg className="w-3.5 h-3.5 text-slate-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M8 16H6a2 2 0 01-2-2V6a2 2 0 012-2h8a2 2 0 012 2v2m-6 12h8a2 2 0 002-2v-8a2 2 0 00-2-2h-8a2 2 0 00-2 2v8a2 2 0 002 2z" />
                  </svg>
                  <span>Copy Dispatch Order</span>
                </>
              )}
            </button>
          )}

          <button
            onClick={fetchBriefing}
            disabled={loading}
            className="text-xs font-mono px-3 py-1.5 rounded bg-indigo-600 hover:bg-indigo-500 disabled:bg-indigo-900/50 text-white transition flex items-center gap-1.5"
          >
            {loading ? (
              <>
                <svg className="w-3.5 h-3.5 animate-spin" viewBox="0 0 24 24" fill="none">
                  <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
                  <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8v8H4z" />
                </svg>
                <span>Analyzing...</span>
              </>
            ) : (
              <>
                <svg className="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" />
                </svg>
                <span>{briefing ? 'Regenerate' : 'Generate AI Briefing'}</span>
              </>
            )}
          </button>
        </div>
      </div>

      {/* Loading Skeleton */}
      {loading && (
        <div className="space-y-4 py-2 animate-pulse">
          <div className="flex items-center gap-3">
            <div className="h-4 bg-slate-800 rounded w-1/4"></div>
            <div className="h-4 bg-slate-800 rounded w-1/6"></div>
          </div>
          <div className="h-16 bg-slate-800/60 rounded-md border border-slate-700/50 p-3">
            <div className="h-3 bg-slate-700 rounded w-full mb-2"></div>
            <div className="h-3 bg-slate-700 rounded w-4/5"></div>
          </div>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
            <div className="h-28 bg-slate-800/40 rounded border border-slate-700/40"></div>
            <div className="h-28 bg-slate-800/40 rounded border border-slate-700/40"></div>
          </div>
          <p className="text-xs text-indigo-400 font-mono text-center">
            Synthesizing hydraulic wave routing telemetry with AI engine...
          </p>
        </div>
      )}

      {/* Error State */}
      {!loading && error && (
        <div className="bg-red-950/40 border border-red-800/50 rounded-lg p-4 text-red-200 text-xs">
          <div className="flex items-start gap-2.5">
            <svg className="w-4 h-4 text-red-400 shrink-0 mt-0.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z" />
            </svg>
            <div>
              <p className="font-semibold mb-1">AI Briefing Generation Error</p>
              <p className="text-red-300/80 mb-3">{error}</p>
              <button
                onClick={fetchBriefing}
                className="px-3 py-1 bg-red-900/60 hover:bg-red-800 text-red-100 rounded border border-red-700 transition text-xs font-mono"
              >
                Retry Generation
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Populated Content */}
      {!loading && !error && briefing && (
        <div className="space-y-4">
          {/* Headline Banner */}
          <div className="bg-slate-800/70 border border-slate-700/70 rounded-md p-3">
            <p className="text-xs font-mono font-medium text-amber-300 mb-1">
              OPERATIONAL SITUATION REPORT:
            </p>
            <p className="text-sm font-semibold text-white">
              {briefing.headline}
            </p>
            <p className="text-xs text-slate-300 mt-2 leading-relaxed">
              {briefing.executive_summary}
            </p>
          </div>

          <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
            {/* Evacuation Timeline */}
            <div className="bg-slate-950/50 border border-slate-800 rounded-md p-3">
              <h4 className="text-xs font-semibold text-slate-300 uppercase tracking-wider mb-2.5 flex items-center gap-2">
                <span className="w-2 h-2 rounded-full bg-red-500"></span>
                Settlement Evacuation Priorities
              </h4>
              {briefing.settlement_timeline.length === 0 ? (
                <p className="text-xs text-slate-500 italic">No settlements in critical impact path.</p>
              ) : (
                <div className="space-y-2 max-h-56 overflow-y-auto pr-1">
                  {briefing.settlement_timeline.map((item, idx) => (
                    <div
                      key={idx}
                      className="bg-slate-900 border border-slate-800 rounded p-2 text-xs flex flex-col gap-1"
                    >
                      <div className="flex items-center justify-between">
                        <span className="font-semibold text-slate-200">
                          {item.name} <span className="text-slate-500 font-normal">({item.district})</span>
                        </span>
                        <div className="flex items-center gap-1.5">
                          <span className="font-mono text-amber-400">T+{item.arrival_time_minutes} min</span>
                          <span className={`px-1.5 py-0.5 rounded text-[10px] font-mono border ${getPriorityBadge(item.evacuation_priority)}`}>
                            {item.evacuation_priority}
                          </span>
                        </div>
                      </div>
                      <p className="text-[11px] text-slate-400 leading-snug">
                        {item.recommended_action}
                      </p>
                    </div>
                  ))}
                </div>
              )}
            </div>

            {/* Tactical Resource Staging */}
            <div className="bg-slate-950/50 border border-slate-800 rounded-md p-3 flex flex-col justify-between">
              <div>
                <h4 className="text-xs font-semibold text-slate-300 uppercase tracking-wider mb-2.5 flex items-center gap-2">
                  <span className="w-2 h-2 rounded-full bg-indigo-500"></span>
                  NDRF / SDRF Deployment Directives
                </h4>
                <ul className="space-y-2 text-xs text-slate-300">
                  {briefing.resource_staging_advisory.map((item, idx) => (
                    <li key={idx} className="flex items-start gap-2">
                      <span className="font-mono text-indigo-400 text-xs mt-0.5 shrink-0">
                        {idx + 1}.
                      </span>
                      <span className="text-slate-300 leading-tight">{item}</span>
                    </li>
                  ))}
                </ul>
              </div>

              {/* Model Attribution Footer */}
              <div className="border-t border-slate-800 pt-3 mt-3 flex items-center justify-between text-[11px] text-slate-500 font-mono">
                <span>Model: {briefing.model_used}</span>
                <span>{briefing.is_fallback ? '🛡️ Expert Rule Engine' : '⚡ AI Generated'}</span>
              </div>
            </div>
          </div>

          {/* Public Alert Bulletin */}
          <div className="bg-amber-950/20 border border-amber-800/40 rounded-md p-3">
            <p className="text-[11px] font-mono uppercase tracking-wider text-amber-400 mb-1">
              Official Siren & Radio Broadcast Bulletin:
            </p>
            <p className="text-xs text-slate-200 font-mono leading-relaxed bg-black/40 p-2 rounded border border-amber-900/30 select-all">
              {briefing.public_advisory_bulletin}
            </p>
          </div>
        </div>
      )}

      {/* Empty State when no briefing requested yet and autoFetch=false */}
      {!loading && !error && !briefing && (
        <div className="text-center py-6">
          <p className="text-xs text-slate-400 mb-3">
            Generate an automated tactical evacuation order and disaster situation briefing for this scenario.
          </p>
          <button
            onClick={fetchBriefing}
            className="text-xs font-mono px-4 py-2 rounded bg-indigo-600 hover:bg-indigo-500 text-white transition"
          >
            Generate AI Briefing
          </button>
        </div>
      )}
    </div>
  );
};
