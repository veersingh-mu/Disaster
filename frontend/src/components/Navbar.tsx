import React, { useEffect, useState } from 'react';
import { Link, useLocation } from 'react-router-dom';
import { API_BASE_URL } from '../services/api';
import { UserProfile } from '../services/auth';

interface NavbarProps {
  currentUser: UserProfile;
  onLogout: () => void;
}

export const Navbar: React.FC<NavbarProps> = ({ currentUser, onLogout }) => {
  const location = useLocation();
  const [isHealthy, setIsHealthy] = useState<boolean | null>(null);
  const [mobileMenuOpen, setMobileMenuOpen] = useState<boolean>(false);

  useEffect(() => {
    const checkHealth = () => {
      if (document.visibilityState !== 'visible') return;
      fetch(`${API_BASE_URL}/health`)
        .then((res) => {
          if (!res.ok) throw new Error();
          setIsHealthy(true);
        })
        .catch(() => setIsHealthy(false));
    };

    checkHealth();
    const interval = setInterval(checkHealth, 15000);
    return () => clearInterval(interval);
  }, []);

  // Close mobile menu upon route change
  useEffect(() => {
    setMobileMenuOpen(false);
  }, [location.pathname]);

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
              const isActive = location.pathname === link.path;
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
          <div
            className="flex items-center gap-space-xs bg-tertiary-container px-2 md:px-space-sm py-1 border border-outline/20"
            title={isHealthy ? 'FastAPI Backend Online' : 'Backend Disconnected'}
          >
            <span
              className={`w-2 h-2 rounded-full ${
                isHealthy === true
                  ? 'bg-emerald-400 animate-pulse'
                  : isHealthy === false
                  ? 'bg-rose-500'
                  : 'bg-amber-400'
              }`}
            />
            <span className="font-mono text-[10px] md:text-[11px] text-on-tertiary-container hidden sm:inline">
              {isHealthy === true ? 'TELEMETRY LIVE' : 'API OFFLINE'}
            </span>
          </div>

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
            const isActive = location.pathname === link.path;
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
    </header>
  );
};
