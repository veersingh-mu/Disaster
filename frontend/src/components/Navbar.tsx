import React, { useEffect, useState } from 'react';
import { Link, useLocation } from 'react-router-dom';
import { getApiBaseUrl, setCustomApiUrl } from '../services/api';
import { UserProfile } from '../services/auth';

interface NavbarProps {
  currentUser: UserProfile;
  onLogout: () => void;
}

export const Navbar: React.FC<NavbarProps> = ({ currentUser, onLogout }) => {
  const location = useLocation();
  const [isHealthy, setIsHealthy] = useState<boolean | null>(null);
  const [mobileMenuOpen, setMobileMenuOpen] = useState<boolean>(false);
  const [settingsOpen, setSettingsOpen] = useState<boolean>(false);
  const [customUrlInput, setCustomUrlInput] = useState<string>('');

  const checkHealth = () => {
    const url = getApiBaseUrl();
    fetch(`${url}/health`)
      .then((res) => {
        if (!res.ok) throw new Error();
        setIsHealthy(true);
      })
      .catch(() => setIsHealthy(false));
  };

  useEffect(() => {
    checkHealth();
    const interval = setInterval(checkHealth, 15000);
    const handleUrlChange = () => {
      checkHealth();
    };
    window.addEventListener('floodpath:api_url_changed', handleUrlChange);
    return () => {
      clearInterval(interval);
      window.removeEventListener('floodpath:api_url_changed', handleUrlChange);
    };
  }, []);

  // Close mobile menu upon route change
  useEffect(() => {
    setMobileMenuOpen(false);
  }, [location.pathname]);

  const handleOpenSettings = () => {
    setCustomUrlInput(getApiBaseUrl());
    setSettingsOpen(true);
  };

  const handleSaveApiUrl = (e: React.FormEvent) => {
    e.preventDefault();
    setCustomApiUrl(customUrlInput.trim() || null);
    setSettingsOpen(false);
    checkHealth();
  };

  const navLinks = [
    { label: 'Operations Dashboard', path: '/', icon: 'dashboard' },
    { label: 'New Scenario', path: '/scenarios/new', icon: 'add_location_alt' },
    { label: 'Historical Benchmarks', path: '/case-studies', icon: 'history_edu' },
  ];

  return (
    <header className="bg-tertiary text-on-tertiary px-space-md md:px-space-lg border-b border-outline/20 sticky top-0 z-50">
      <div className="h-[48px] flex items-center justify-between">
        {/* Brand & Section Indicator */}
        <div className="flex items-center gap-space-sm md:gap-space-md">
          {/* Mobile Hamburger Button */}
          <button
            onClick={() => setMobileMenuOpen((prev) => !prev)}
            className="md:hidden p-1.5 text-tertiary-fixed hover:text-white transition-colors"
            aria-label="Toggle navigation menu"
            aria-expanded={mobileMenuOpen}
          >
            <span className="material-symbols-outlined text-xl">
              {mobileMenuOpen ? 'close' : 'menu'}
            </span>
          </button>

          <Link to="/" className="flex items-center gap-space-xs hover:opacity-90 transition-opacity">
            <span className="material-symbols-outlined text-primary-fixed text-xl">water_voc</span>
            <span className="font-semibold text-base tracking-tight text-white font-heading">
              FloodPath
            </span>
          </Link>
          <span className="hidden sm:inline-block font-mono text-[10px] md:text-[11px] bg-tertiary-container text-on-tertiary-container px-space-xs py-space-2xs uppercase tracking-wider font-semibold border border-outline/20">
            SIH 26161
          </span>

          {/* Desktop Navigation Tabs */}
          <nav className="hidden md:flex items-center gap-1 ml-4 border-l border-tertiary-container pl-4">
            {navLinks.map((link) => {
              const isActive =
                link.path === '/'
                  ? location.pathname === '/' || location.pathname === '/dashboard'
                  : location.pathname === link.path;
              return (
                <Link
                  key={link.path}
                  to={link.path}
                  className={`flex items-center gap-1.5 px-3 py-1 text-xs font-medium transition-colors ${
                    isActive
                      ? 'bg-primary-container text-white border-b-2 border-primary-fixed'
                      : 'text-tertiary-fixed hover:text-white hover:bg-tertiary-container'
                  }`}
                >
                  <span className="material-symbols-outlined text-sm">{link.icon}</span>
                  <span>{link.label}</span>
                </Link>
              );
            })}
          </nav>
        </div>

        {/* Status & User Profile Actions */}
        <div className="flex items-center gap-2 md:gap-space-md">
          {/* Backend Heartbeat */}
          <button
            onClick={handleOpenSettings}
            className="flex items-center gap-space-xs bg-tertiary-container hover:bg-tertiary-container/80 px-2 md:px-space-sm py-1 border border-outline/20 transition-colors text-left"
            title="Click to view or configure Backend API endpoint"
          >
            <span
              className={`w-2 h-2 rounded-full ${
                isHealthy === true
                  ? 'bg-emerald-400 animate-pulse'
                  : isHealthy === false
                  ? 'bg-amber-400'
                  : 'bg-zinc-400'
              }`}
            />
            <span className="font-mono text-[10px] md:text-[11px] text-on-tertiary-container hidden sm:inline">
              {isHealthy === true
                ? 'TELEMETRY LIVE'
                : isHealthy === false
                ? 'STANDALONE (DEMO)'
                : 'CHECKING...'}
            </span>
            <span className="material-symbols-outlined text-xs text-tertiary-fixed hidden sm:inline">
              tune
            </span>
          </button>

          {/* User Badge & Logout */}
          <div className="flex items-center gap-2 md:gap-space-sm border-l border-tertiary-container pl-2 md:pl-space-md">
            <div className="text-right text-xs max-w-[120px] md:max-w-[170px]">
              <div className="font-semibold text-white truncate text-[11px] md:text-[12px]">
                {currentUser.email}
              </div>
              <div className="font-mono text-primary-fixed-dim text-[9px] md:text-[10px] uppercase font-bold tracking-wider">
                {currentUser.role}
              </div>
            </div>
            <button
              onClick={onLogout}
              title="Sign Out"
              aria-label="Sign Out"
              className="p-1.5 hover:bg-tertiary-container text-tertiary-fixed hover:text-white transition-colors flex items-center justify-center"
            >
              <span className="material-symbols-outlined text-base">logout</span>
            </button>
          </div>
        </div>
      </div>

      {/* Mobile Drawer Dropdown */}
      {mobileMenuOpen && (
        <div className="md:hidden py-2 border-t border-outline/20 flex flex-col gap-1 bg-tertiary pb-3">
          {navLinks.map((link) => {
            const isActive =
              link.path === '/'
                ? location.pathname === '/' || location.pathname === '/dashboard'
                : location.pathname === link.path;
            return (
              <Link
                key={link.path}
                to={link.path}
                className={`flex items-center gap-2 px-3 py-2 text-xs font-medium transition-colors ${
                  isActive
                    ? 'bg-primary-container text-white font-bold'
                    : 'text-tertiary-fixed hover:text-white hover:bg-tertiary-container'
                }`}
              >
                <span className="material-symbols-outlined text-sm">{link.icon}</span>
                <span>{link.label}</span>
              </Link>
            );
          })}
        </div>
      )}

      {/* API Configuration Modal */}
      {settingsOpen && (
        <div className="fixed inset-0 z-50 bg-black/50 backdrop-blur-xs flex items-center justify-center p-4">
          <div className="bg-surface-container-lowest border border-outline/30 p-space-lg w-full max-w-md shadow-xl text-on-surface">
            <div className="flex items-center justify-between border-b border-outline/20 pb-3 mb-4">
              <div className="flex items-center gap-2">
                <span className="material-symbols-outlined text-primary text-xl">tune</span>
                <h3 className="font-heading font-bold text-base">Backend Telemetry Settings</h3>
              </div>
              <button
                onClick={() => setSettingsOpen(false)}
                className="text-secondary hover:text-on-surface"
              >
                <span className="material-symbols-outlined text-lg">close</span>
              </button>
            </div>

            <div className="text-xs text-on-surface-variant mb-4 space-y-2">
              <p>
                FloodPath connects to a FastAPI hydrodynamic solver. In cloud deployments without a
                remote backend, the app automatically runs in <strong>Standalone Benchmark Mode</strong>{' '}
                using pre-calibrated historical hydrodynamic data (Rishi Ganga &amp; South Lhonak).
              </p>
              <div className="p-2 bg-surface-container-low border border-outline/20 font-mono text-[11px] flex items-center justify-between">
                <span>Active Connection:</span>
                <span
                  className={`font-bold ${
                    isHealthy ? 'text-emerald-600' : 'text-amber-600'
                  }`}
                >
                  {isHealthy ? 'TELEMETRY LIVE' : 'STANDALONE BENCHMARK'}
                </span>
              </div>
            </div>

            <form onSubmit={handleSaveApiUrl} className="space-y-4">
              <div>
                <label className="block text-[11px] font-mono font-semibold uppercase text-secondary mb-1">
                  API Endpoint URL
                </label>
                <input
                  type="text"
                  value={customUrlInput}
                  onChange={(e) => setCustomUrlInput(e.target.value)}
                  placeholder="e.g., https://your-backend-domain.com or http://localhost:8000"
                  className="w-full text-xs font-mono p-2 border border-outline/40 bg-surface-container-lowest text-on-surface focus:outline-none focus:border-primary"
                />
              </div>

              <div className="flex items-center justify-between pt-2">
                <button
                  type="button"
                  onClick={() => {
                    setCustomApiUrl(null);
                    setCustomUrlInput(getApiBaseUrl());
                    checkHealth();
                  }}
                  className="text-xs text-secondary hover:text-on-surface underline font-mono"
                >
                  Reset to Default
                </button>

                <div className="flex items-center gap-2">
                  <button
                    type="button"
                    onClick={() => setSettingsOpen(false)}
                    className="px-3 py-1.5 text-xs bg-surface-container border border-outline/30 hover:bg-surface-container-high font-medium"
                  >
                    Close
                  </button>
                  <button
                    type="submit"
                    className="px-4 py-1.5 text-xs bg-primary text-on-primary font-semibold hover:bg-primary-container transition-colors"
                  >
                    Save &amp; Reconnect
                  </button>
                </div>
              </div>
            </form>
          </div>
        </div>
      )}
    </header>
  );
};

