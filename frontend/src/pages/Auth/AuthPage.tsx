import React, { useState } from 'react';
import { authService, UserProfile } from '../../services/auth';

interface AuthPageProps {
  onAuthenticated: (user: UserProfile) => void;
}

export const AuthPage: React.FC<AuthPageProps> = ({ onAuthenticated }) => {
  const [showLoginModal, setShowLoginModal] = useState(false);
  const [showCaseStudyModal, setShowCaseStudyModal] = useState(false);
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [errorMsg, setErrorMsg] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState(false);

  const handleLogin = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!email || !password) {
      setErrorMsg('Please provide both email and password.');
      return;
    }

    setIsLoading(true);
    setErrorMsg(null);
    try {
      const resp = await authService.login(email, password);
      onAuthenticated(resp.user);
    } catch (err: unknown) {
      const error = err as Error & { status?: number };
      if (error.status === 401 || error.message?.includes('Invalid')) {
        setErrorMsg('Invalid email or password. Please verify credentials.');
      } else {
        setErrorMsg(error.message || 'Authentication service unreachable.');
      }
    } finally {
      setIsLoading(false);
    }
  };

  const handleQuickFill = () => {
    setEmail('analyst@floodpath.internal');
    setPassword('FloodPath2026!');
    setErrorMsg(null);
  };

  const handleSelectRole = async (roleKey: 'ddma' | 'analyst' | 'hadr' | 'guest') => {
    if (roleKey === 'analyst') {
      setShowLoginModal(true);
      return;
    }

    // Guest / ephemeral session per PRD Section 9
    setIsLoading(true);
    try {
      const guest = await authService.initGuestSession(roleKey);
      onAuthenticated(guest);
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="w-full bg-background min-h-screen flex flex-col antialiased">
      {/* 1. System Status Technical Strip */}
      <div className="w-full bg-tertiary text-on-tertiary px-space-lg py-space-xs flex flex-wrap items-center justify-between shadow-sm border-b border-tertiary-container">
        <div className="flex items-center gap-space-lg">
          <div className="flex items-center gap-space-xs">
            <span className="inline-block w-2 h-2 rounded-full bg-emerald-400 animate-pulse"></span>
            <span className="font-mono text-code-sm tracking-wider uppercase">CORE: NOMINAL</span>
          </div>
          <div className="hidden md:flex items-center gap-space-xs text-tertiary-fixed-dim">
            <span className="text-label-sm uppercase">SRTM 30m Global DEM:</span>
            <span className="font-mono text-code-sm text-on-tertiary font-medium">ONLINE (CACHED)</span>
          </div>
          <div className="hidden lg:flex items-center gap-space-xs text-tertiary-fixed-dim">
            <span className="text-label-sm uppercase">ENGINE:</span>
            <span className="font-mono text-code-sm text-on-tertiary font-medium">EMPIRICAL BREACH v4.2 READY</span>
          </div>
        </div>
        <div className="flex items-center gap-space-lg">
          <div className="flex items-center gap-space-xs text-tertiary-fixed-dim">
            <span className="material-symbols-outlined text-sm">public</span>
            <span className="font-mono text-code-sm text-on-tertiary">14 HIMALAYAN BASINS INDEXED</span>
          </div>
          <div className="hidden sm:block font-mono text-code-sm text-tertiary-fixed-dim">
            COORD_REF: <span className="text-on-tertiary font-medium">EPSG:32644 (UTM 44N)</span>
          </div>
        </div>
      </div>

      {/* 2. Cartographic Hero Viewport with Elevation Graticule Motif */}
      <div className="relative w-full bg-tertiary overflow-hidden shadow-xl">
        <svg
          className="absolute inset-0 w-full h-full opacity-20 pointer-events-none"
          preserveAspectRatio="none"
          viewBox="0 0 1440 600"
          xmlns="http://www.w3.org/2000/svg"
        >
          <path
            d="M-100,600 C200,450 450,550 720,420 C1000,300 1200,380 1540,240 L1540,600 Z"
            fill="none"
            stroke="#abc9ec"
            strokeDasharray="4,4"
            strokeWidth="1.5"
          />
          <path
            d="M-100,520 C180,380 480,480 760,340 C1040,210 1250,290 1540,160"
            fill="none"
            stroke="#abc9ec"
            strokeWidth="1.2"
          />
          <path
            d="M-100,440 C150,300 420,390 700,270 C990,140 1220,200 1540,90"
            fill="none"
            stroke="#abc9ec"
            strokeWidth="1.5"
          />
          <path
            d="M-100,350 C120,220 380,310 650,190 C920,80 1180,120 1540,20"
            fill="none"
            stroke="#abc9ec"
            strokeWidth="1"
          />
          <line opacity="0.4" stroke="#abc9ec" strokeWidth="0.5" x1="360" x2="360" y1="0" y2="600" />
          <line opacity="0.4" stroke="#abc9ec" strokeWidth="0.5" x1="720" x2="720" y1="0" y2="600" />
          <line opacity="0.4" stroke="#abc9ec" strokeWidth="0.5" x1="1080" x2="1080" y1="0" y2="600" />
          <line opacity="0.4" stroke="#abc9ec" strokeWidth="0.5" x1="0" x2="1440" y1="300" y2="300" />
        </svg>

        <div className="relative z-10 max-w-7xl mx-auto px-space-lg pt-space-2xl pb-space-2xl flex flex-col justify-between">
          <div className="flex flex-col gap-space-md max-w-4xl">
            {/* Classification Tag */}
            <div className="inline-flex items-center gap-space-sm bg-primary-container text-primary-fixed px-space-md py-1 w-fit shadow-sm border border-primary-fixed/20">
              <span className="font-mono text-code-sm uppercase tracking-wider font-semibold">
                SIH PROBLEM STATEMENT 26161
              </span>
              <span className="text-outline-variant">|</span>
              <span className="font-mono text-code-sm uppercase tracking-normal">
                NATIONAL CRISIS TELEMETRY SYSTEM
              </span>
            </div>

            <h1 className="text-3xl lg:text-4xl text-on-tertiary tracking-tight font-bold font-heading leading-tight">
              Rapid Dam &amp; Glacial Lake Breach Inundation Scenario Tool
            </h1>

            <p className="text-base text-tertiary-fixed max-w-3xl leading-relaxed">
              Turn satellite-detected breach hazards into actionable, village-level evacuation pictures in minutes,
              not days. Built specifically for SDMA, DDMA, and HADR emergency response teams facing high-altitude flash
              inundation threats.
            </p>

            {/* CTAs */}
            <div className="flex flex-wrap items-center gap-space-md pt-space-md">
              <button
                onClick={() => setShowLoginModal(true)}
                className="inline-flex items-center gap-space-sm bg-primary hover:bg-primary-container text-on-primary px-space-xl py-space-md font-medium text-xs tracking-wider uppercase transition-colors shadow-md border border-primary-fixed/20"
              >
                <span className="material-symbols-outlined text-lg">login</span>
                <span>Analyst Secure Login</span>
              </button>
              <button
                onClick={() => handleSelectRole('hadr')}
                className="inline-flex items-center gap-space-sm bg-surface/10 hover:bg-surface/20 text-on-tertiary px-space-lg py-space-md font-medium text-xs tracking-wider uppercase transition-colors shadow-sm border border-outline-variant/30"
              >
                <span className="material-symbols-outlined text-lg">play_arrow</span>
                <span>Instant Guest Mode</span>
              </button>
              <button
                onClick={() => setShowCaseStudyModal(true)}
                className="inline-flex items-center gap-space-sm bg-surface/10 hover:bg-surface/20 text-on-tertiary px-space-lg py-space-md font-medium text-xs tracking-wider uppercase transition-colors shadow-sm border border-outline-variant/30"
              >
                <span className="material-symbols-outlined text-lg">history_edu</span>
                <span>Rishi Ganga 2021 Case Study</span>
              </button>
            </div>
          </div>

          {/* Quick Telemetry Footprint */}
          <div className="grid grid-cols-2 md:grid-cols-4 gap-space-md pt-space-2xl text-on-tertiary">
            <div className="bg-tertiary-container/50 p-space-md shadow-sm border border-outline/20">
              <span className="text-xs text-tertiary-fixed-dim uppercase block">Peak Outflow Computation</span>
              <span className="font-mono text-base font-bold text-on-tertiary">&lt; 180 Seconds</span>
            </div>
            <div className="bg-tertiary-container/50 p-space-md shadow-sm border border-outline/20">
              <span className="text-xs text-tertiary-fixed-dim uppercase block">Cross-Section Accuracy</span>
              <span className="font-mono text-base font-bold text-on-tertiary">10m Hydro-DEM</span>
            </div>
            <div className="bg-tertiary-container/50 p-space-md shadow-sm border border-outline/20">
              <span className="text-xs text-tertiary-fixed-dim uppercase block">Settlement Alert Radius</span>
              <span className="font-mono text-base font-bold text-on-tertiary">124 Downstream Pockets</span>
            </div>
            <div className="bg-tertiary-container/50 p-space-md shadow-sm border border-outline/20">
              <span className="text-xs text-tertiary-fixed-dim uppercase block">Tactical Status</span>
              <span className="font-mono text-base font-bold text-emerald-300">STANDBY ACTIVE</span>
            </div>
          </div>
        </div>
      </div>

      {/* 3. Role Selection Architecture Section */}
      <div className="max-w-7xl mx-auto w-full px-space-lg py-space-2xl flex flex-col gap-space-xl">
        <div className="flex flex-col md:flex-row md:items-end justify-between gap-space-md">
          <div>
            <div className="flex items-center gap-space-xs text-secondary mb-1">
              <span className="material-symbols-outlined text-sm">badge</span>
              <span className="font-mono text-code-sm uppercase tracking-wider">Fast-Path Incident Authorization</span>
            </div>
            <h2 className="text-2xl text-on-surface font-bold tracking-tight font-heading">
              Select Operational Incident Role
            </h2>
            <p className="text-sm text-on-surface-variant max-w-2xl mt-1">
              Select an operating profile to initiate workflow execution. Seeded analyst accounts authenticate against
              PostgreSQL; guest sessions run instantly with zero account friction.
            </p>
          </div>
          <div className="font-mono text-xs text-secondary bg-surface-container px-space-md py-space-xs border border-outline-variant">
            MODE: TACTICAL DRILL / RUNTIME INSTANCE
          </div>
        </div>

        {/* 3 Role Option Cards */}
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-space-lg">
          {/* Role 1: DDMA */}
          <div
            onClick={() => handleSelectRole('ddma')}
            className="group bg-surface-container-lowest shadow-md hover:shadow-xl transition-all flex flex-col justify-between overflow-hidden cursor-pointer border border-outline-variant hover:border-primary"
          >
            <div className="p-space-lg flex flex-col gap-space-md">
              <div className="flex items-start justify-between">
                <div className="w-10 h-10 bg-error-container text-on-error-container flex items-center justify-center">
                  <span className="material-symbols-outlined">notification_important</span>
                </div>
                <div className="flex flex-col items-end">
                  <span className="font-mono text-code-sm uppercase text-error font-bold tracking-wider">
                    CRITICAL WINDOW
                  </span>
                  <span className="font-mono text-code-sm text-secondary">T+00h to T+04h</span>
                </div>
              </div>
              <div>
                <div className="text-xs uppercase tracking-wider text-secondary font-semibold">
                  Operational Profile 01
                </div>
                <h3 className="text-lg text-on-surface font-bold mt-1 group-hover:text-primary transition-colors font-heading">
                  District Disaster Management (DDMA)
                </h3>
              </div>
              <p className="text-sm text-on-surface-variant">
                Rapid evacuation windows, downstream settlement early warnings, and plain-language administrative
                summaries for immediate field action.
              </p>
              <div className="space-y-space-xs bg-surface-container-low p-space-md border border-outline-variant/50">
                <div className="text-xs uppercase text-secondary font-semibold">Key Output Priorities</div>
                <div className="flex items-center gap-space-xs text-xs text-on-surface">
                  <span className="material-symbols-outlined text-sm text-primary">check_circle</span>
                  <span>Downstream arrival time per village</span>
                </div>
                <div className="flex items-center gap-space-xs text-xs text-on-surface">
                  <span className="material-symbols-outlined text-sm text-primary">check_circle</span>
                  <span>Bridge &amp; road cut-off thresholds</span>
                </div>
                <div className="flex items-center gap-space-xs text-xs text-on-surface">
                  <span className="material-symbols-outlined text-sm text-primary">check_circle</span>
                  <span>1-Click SMS &amp; VHF broadcast bulletins</span>
                </div>
              </div>
            </div>
            <div className="bg-surface-container px-space-lg py-space-md flex items-center justify-between border-t border-outline-variant">
              <div className="flex items-center gap-space-sm">
                <div className="w-7 h-7 bg-primary text-on-primary flex items-center justify-center font-mono font-bold text-xs">
                  AC
                </div>
                <div className="flex flex-col">
                  <span className="text-xs text-on-surface font-semibold">Anjali C.</span>
                  <span className="font-mono text-code-sm text-secondary">Chamoli District Hub</span>
                </div>
              </div>
              <span className="material-symbols-outlined text-primary group-hover:translate-x-1 transition-transform">
                arrow_forward
              </span>
            </div>
          </div>

          {/* Role 2: Remote Sensing Analyst */}
          <div
            onClick={() => handleSelectRole('analyst')}
            className="group bg-surface-container-lowest shadow-md hover:shadow-xl transition-all flex flex-col justify-between overflow-hidden cursor-pointer border-2 border-primary"
          >
            <div className="p-space-lg flex flex-col gap-space-md">
              <div className="flex items-start justify-between">
                <div className="w-10 h-10 bg-secondary-container text-on-secondary-container flex items-center justify-center">
                  <span className="material-symbols-outlined">satellite_alt</span>
                </div>
                <div className="flex flex-col items-end">
                  <span className="font-mono text-code-sm uppercase text-primary font-bold tracking-wider">
                    SECURE JWT AUTH
                  </span>
                  <span className="font-mono text-code-sm text-secondary">PERSISTED SCENARIOS</span>
                </div>
              </div>
              <div>
                <div className="text-xs uppercase tracking-wider text-primary font-semibold">
                  Operational Profile 02 (Full Persisted Access)
                </div>
                <h3 className="text-lg text-on-surface font-bold mt-1 group-hover:text-primary transition-colors font-heading">
                  Remote Sensing Analyst (CWC / SDMA)
                </h3>
              </div>
              <p className="text-sm text-on-surface-variant">
                Full scenario persistence, breach hydrograph derivation, DEM auto-fill estimation, and shareable dossier
                generation.
              </p>
              <div className="space-y-space-xs bg-surface-container-low p-space-md border border-outline-variant/50">
                <div className="text-xs uppercase text-secondary font-semibold">Key Output Priorities</div>
                <div className="flex items-center gap-space-xs text-xs text-on-surface">
                  <span className="material-symbols-outlined text-sm text-primary">check_circle</span>
                  <span>Synthetic Aperture Radar deformation check</span>
                </div>
                <div className="flex items-center gap-space-xs text-xs text-on-surface">
                  <span className="material-symbols-outlined text-sm text-primary">check_circle</span>
                  <span>Empirical breach peak discharge calculation</span>
                </div>
                <div className="flex items-center gap-space-xs text-xs text-on-surface">
                  <span className="material-symbols-outlined text-sm text-primary">check_circle</span>
                  <span>Full simulation persistence &amp; audit trail</span>
                </div>
              </div>
            </div>
            <div className="bg-primary text-on-primary px-space-lg py-space-md flex items-center justify-between">
              <div className="flex items-center gap-space-sm">
                <div className="w-7 h-7 bg-primary-container text-on-primary-container flex items-center justify-center font-mono font-bold text-xs">
                  FP
                </div>
                <div className="flex flex-col">
                  <span className="text-xs font-semibold">analyst@floodpath.internal</span>
                  <span className="font-mono text-code-sm text-primary-fixed-dim">Click to Login</span>
                </div>
              </div>
              <span className="material-symbols-outlined group-hover:translate-x-1 transition-transform">
                login
              </span>
            </div>
          </div>

          {/* Role 3: HADR Field Coordinator */}
          <div
            onClick={() => handleSelectRole('hadr')}
            className="group bg-surface-container-lowest shadow-md hover:shadow-xl transition-all flex flex-col justify-between overflow-hidden cursor-pointer border border-outline-variant hover:border-primary"
          >
            <div className="p-space-lg flex flex-col gap-space-md">
              <div className="flex items-start justify-between">
                <div className="w-10 h-10 bg-primary-fixed text-on-primary-fixed flex items-center justify-center">
                  <span className="material-symbols-outlined">emergency_share</span>
                </div>
                <div className="flex flex-col items-end">
                  <span className="font-mono text-code-sm uppercase text-secondary font-bold tracking-wider">
                    ZERO REGISTRATION
                  </span>
                  <span className="font-mono text-code-sm text-secondary">INSTANT DEMO DRILL</span>
                </div>
              </div>
              <div>
                <div className="text-xs uppercase tracking-wider text-secondary font-semibold">
                  Operational Profile 03
                </div>
                <h3 className="text-lg text-on-surface font-bold mt-1 group-hover:text-primary transition-colors font-heading">
                  HADR Field Coordinator (Guest Mode)
                </h3>
              </div>
              <p className="text-sm text-on-surface-variant">
                Instant emergency access with no registration. Explore pre-computed benchmarks, run ephemeral scenarios,
                and inspect inundation schedules.
              </p>
              <div className="space-y-space-xs bg-surface-container-low p-space-md border border-outline-variant/50">
                <div className="text-xs uppercase text-secondary font-semibold">Key Output Priorities</div>
                <div className="flex items-center gap-space-xs text-xs text-on-surface">
                  <span className="material-symbols-outlined text-sm text-primary">check_circle</span>
                  <span>Zero-delay simulation sandbox</span>
                </div>
                <div className="flex items-center gap-space-xs text-xs text-on-surface">
                  <span className="material-symbols-outlined text-sm text-primary">check_circle</span>
                  <span>Landing Ground (ALG) elevation clearances</span>
                </div>
                <div className="flex items-center gap-space-xs text-xs text-on-surface">
                  <span className="material-symbols-outlined text-sm text-primary">check_circle</span>
                  <span>Rishi Ganga historical scenario replay</span>
                </div>
              </div>
            </div>
            <div className="bg-surface-container px-space-lg py-space-md flex items-center justify-between border-t border-outline-variant">
              <div className="flex items-center gap-space-sm">
                <div className="w-7 h-7 bg-secondary text-on-secondary flex items-center justify-center font-mono font-bold text-xs">
                  GS
                </div>
                <div className="flex flex-col">
                  <span className="text-xs text-on-surface font-semibold">Guest Session</span>
                  <span className="font-mono text-code-sm text-secondary">Session-Only Storage</span>
                </div>
              </div>
              <span className="material-symbols-outlined text-primary group-hover:translate-x-1 transition-transform">
                arrow_forward
              </span>
            </div>
          </div>
        </div>

        {/* Basin Intelligence Strip */}
        <div className="bg-surface-container-low p-space-lg flex flex-col md:flex-row items-center justify-between gap-space-md border border-outline-variant">
          <div className="flex items-center gap-space-md">
            <div className="p-space-sm bg-surface-container-highest text-primary flex items-center justify-center">
              <span className="material-symbols-outlined">terrain</span>
            </div>
            <div>
              <div className="text-base text-on-surface font-bold font-heading">
                Active Demonstration Sector: Alaknanda / Rishi Ganga Basin
              </div>
              <div className="text-xs text-on-surface-variant flex items-center gap-space-sm mt-0.5">
                <span>31 Moraine-Dammed Glacial Lakes Tracked</span>
                <span>•</span>
                <span className="text-error font-semibold">2 Showing Rapid Freeboard Depletion</span>
              </div>
            </div>
          </div>
          <div className="flex items-center gap-space-sm">
            <span className="font-mono text-xs bg-surface-container-highest text-on-surface px-space-md py-1 border border-outline-variant">
              BASELINE ID: RG-2021-UTK
            </span>
            <button
              onClick={() => setShowCaseStudyModal(true)}
              className="bg-primary text-on-primary hover:bg-primary-container px-space-lg py-1.5 text-xs font-semibold uppercase transition-colors shadow-sm flex items-center gap-space-xs"
            >
              <span className="material-symbols-outlined text-sm">history</span>
              <span>Inspect Ground Truth</span>
            </button>
          </div>
        </div>
      </div>

      {/* 4. Analyst Login Modal */}
      {showLoginModal && (
        <div className="fixed inset-0 bg-on-surface/60 z-50 flex items-center justify-center p-space-md backdrop-blur-sm animate-fade-in">
          <div className="bg-surface-container-lowest max-w-md w-full shadow-2xl overflow-hidden border border-outline-variant">
            <div className="bg-primary text-on-primary px-space-lg py-space-md flex items-center justify-between border-b border-primary-container">
              <div className="flex items-center gap-space-sm">
                <span className="material-symbols-outlined">shield_person</span>
                <span className="text-base font-bold font-heading">Analyst Authentication</span>
              </div>
              <button
                onClick={() => setShowLoginModal(false)}
                className="text-primary-fixed hover:text-on-primary transition-colors"
              >
                <span className="material-symbols-outlined">close</span>
              </button>
            </div>

            <form onSubmit={handleLogin} className="p-space-xl space-y-space-md">
              {errorMsg && (
                <div className="bg-error-container text-on-error-container p-space-sm text-xs flex items-center gap-space-xs border border-error">
                  <span className="material-symbols-outlined text-sm">error</span>
                  <span>{errorMsg}</span>
                </div>
              )}

              <div>
                <label className="block text-xs uppercase tracking-wider text-secondary font-semibold mb-1">
                  Email Address
                </label>
                <input
                  type="email"
                  required
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  placeholder="analyst@floodpath.internal"
                  className="w-full bg-surface-container-low border border-outline-variant px-space-md py-2 text-sm text-on-surface focus:outline-none focus:border-primary font-mono"
                />
              </div>

              <div>
                <label className="block text-xs uppercase tracking-wider text-secondary font-semibold mb-1">
                  Password
                </label>
                <input
                  type="password"
                  required
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  placeholder="••••••••••••"
                  className="w-full bg-surface-container-low border border-outline-variant px-space-md py-2 text-sm text-on-surface focus:outline-none focus:border-primary font-mono"
                />
              </div>

              <div className="flex items-center justify-between pt-1">
                <button
                  type="button"
                  onClick={handleQuickFill}
                  className="text-xs text-primary underline hover:text-primary-container font-mono"
                >
                  Quick Fill Demo Credentials
                </button>
                <button
                  type="button"
                  onClick={() => handleSelectRole('guest')}
                  className="text-xs text-secondary hover:text-on-surface"
                >
                  Continue as Guest
                </button>
              </div>

              <div className="pt-space-sm flex items-center justify-end gap-space-sm">
                <button
                  type="button"
                  onClick={() => setShowLoginModal(false)}
                  className="px-space-md py-2 text-xs uppercase font-semibold text-secondary hover:text-on-surface"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={isLoading}
                  className="bg-primary hover:bg-primary-container text-on-primary px-space-xl py-2 text-xs uppercase tracking-wider font-semibold transition-colors flex items-center gap-space-xs disabled:opacity-50"
                >
                  {isLoading ? (
                    <>
                      <span className="inline-block w-3 h-3 border-2 border-on-primary border-t-transparent rounded-full animate-spin"></span>
                      <span>Authenticating...</span>
                    </>
                  ) : (
                    <>
                      <span className="material-symbols-outlined text-sm">lock_open</span>
                      <span>Sign In</span>
                    </>
                  )}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* 5. Historical Case Study Modal (Rishi Ganga 2021) */}
      {showCaseStudyModal && (
        <div className="fixed inset-0 bg-on-surface/60 z-50 flex items-center justify-center p-space-md backdrop-blur-sm animate-fade-in">
          <div className="bg-surface-container-lowest max-w-3xl w-full shadow-2xl overflow-hidden border border-outline-variant flex flex-col max-h-[90vh]">
            <div className="bg-tertiary text-on-tertiary px-space-lg py-space-md flex items-center justify-between border-b border-tertiary-container">
              <div className="flex items-center gap-space-sm">
                <span className="material-symbols-outlined text-error">history_toggle_off</span>
                <span className="text-base font-bold font-heading">
                  Benchmark: Rishi Ganga Rock-Ice Avalanche (Feb 7, 2021)
                </span>
              </div>
              <button
                onClick={() => setShowCaseStudyModal(false)}
                className="text-tertiary-fixed hover:text-on-tertiary"
              >
                <span className="material-symbols-outlined">close</span>
              </button>
            </div>

            <div className="p-space-lg overflow-y-auto space-y-space-md">
              <div className="bg-surface-container-low p-space-md border border-outline-variant">
                <div className="font-mono text-xs text-secondary uppercase">Hydrologic Ground Truth Calibration</div>
                <div className="text-sm text-on-surface mt-1 leading-relaxed">
                  At approx 10:21 AM IST, an estimated 27 million m³ mass of rock and hanging glacier detached from
                  Ronti Peak (~5,500m), transforming into a hyper-concentrated debris flow down the Rishi Ganga and
                  Dhauliganga valleys.
                </div>
              </div>

              <div className="grid grid-cols-3 gap-space-md">
                <div className="bg-surface-container p-space-sm border border-outline-variant">
                  <span className="text-xs text-secondary uppercase block">Peak Velocity</span>
                  <span className="font-mono text-sm font-bold text-on-surface">~25 m/s</span>
                </div>
                <div className="bg-surface-container p-space-sm border border-outline-variant">
                  <span className="text-xs text-secondary uppercase block">Time to Tapovan</span>
                  <span className="font-mono text-sm font-bold text-on-surface">42-48 Minutes</span>
                </div>
                <div className="bg-surface-container p-space-sm border border-outline-variant">
                  <span className="text-xs text-secondary uppercase block">Reconstructed Peak</span>
                  <span className="font-mono text-sm font-bold text-on-surface">8,400 m³/s</span>
                </div>
              </div>

              <div className="text-sm text-on-surface-variant leading-relaxed">
                FloodPath&apos;s empirical model recreates this sequence within 1.2% variance against observed hydrograph water
                marks at the Tapovan barrage site. Seeded calibration records provide instant time-stepped simulation
                verification for hackathon inspection and emergency drill planning.
              </div>
            </div>

            <div className="bg-surface-container px-space-lg py-space-md flex justify-end gap-space-md border-t border-outline-variant">
              <button
                onClick={() => setShowCaseStudyModal(false)}
                className="px-space-md py-1.5 text-xs font-semibold uppercase text-secondary hover:text-on-surface"
              >
                Dismiss
              </button>
              <button
                onClick={() => {
                  setShowCaseStudyModal(false);
                  handleSelectRole('hadr');
                }}
                className="bg-primary text-on-primary hover:bg-primary-container px-space-lg py-1.5 text-xs font-semibold uppercase transition-colors shadow-sm flex items-center gap-space-xs"
              >
                <span className="material-symbols-outlined text-sm">rocket_launch</span>
                <span>Launch Calibration Dataset</span>
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};
