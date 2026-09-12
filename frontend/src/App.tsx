import { useEffect, useState } from 'react';
import { BrowserRouter, Navigate, Route, Routes } from 'react-router-dom';
import { Navbar } from './components/Navbar';
import { AuthPage } from './pages/Auth/AuthPage';
import { CaseStudiesPage } from './pages/CaseStudies/CaseStudiesPage';
import { DashboardPage } from './pages/Dashboard/DashboardPage';
import { ResultsPage } from './pages/Results/ResultsPage';
import { SimulationLoadingPage } from './pages/Simulation/SimulationLoadingPage';
import { SiteSelectionPage } from './pages/SiteSelection/SiteSelectionPage';
import { authService, UserProfile } from './services/auth';

export default function App() {
  const [currentUser, setCurrentUser] = useState<UserProfile | null>(() => authService.getUser());

  useEffect(() => {
    const handleAuthError = () => {
      setCurrentUser(null);
    };
    window.addEventListener('floodpath:auth_error', handleAuthError);
    return () => window.removeEventListener('floodpath:auth_error', handleAuthError);
  }, []);

  const handleLogout = () => {
    authService.logout();
    setCurrentUser(null);
  };

  if (!currentUser) {
    return <AuthPage onAuthenticated={(user) => setCurrentUser(user)} />;
  }

  return (
    <BrowserRouter>
      <div className="min-h-screen bg-background text-on-surface flex flex-col font-body">
        <Navbar currentUser={currentUser} onLogout={handleLogout} />
        <main className="flex-1 flex flex-col">
          <Routes>
            <Route path="/" element={<DashboardPage />} />
            <Route path="/scenarios/new" element={<SiteSelectionPage />} />
            <Route path="/scenarios/:id/simulating" element={<SimulationLoadingPage />} />
            <Route path="/scenarios/:id/results" element={<ResultsPage />} />
            <Route path="/case-studies" element={<CaseStudiesPage />} />
            <Route path="/case-studies/:id/results" element={<ResultsPage />} />
            <Route path="*" element={<Navigate to="/" replace />} />
          </Routes>
        </main>
      </div>
    </BrowserRouter>
  );
}
