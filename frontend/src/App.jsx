import React, { useState, useEffect } from 'react';
import { Navbar, Footer } from './components';
import { LandingPage, MapViewPage } from './pages';
import { 
  GridOperatorDashboard, 
  UtilityDashboard, 
  PlantOwnerDashboard, 
  EnergyTraderDashboard 
} from './components/dashboards';
import AuthModal from './components/Auth/AuthModal';
import { AuthProvider, useAuth } from './context/AuthContext';
import { checkBackendHealth } from './services/api';
import { LayoutDashboard, Compass, Layers, ShieldCheck, Sparkles, UserCheck } from 'lucide-react';

function AppContent() {
  const { user, isAuthenticated, setTemporaryRole } = useAuth();
  const [backendHealth, setBackendHealth] = useState({ status: 'connecting', database: 'probing' });
  const [activeRole, setActiveRole] = useState('grid-operator');
  const [activeView, setActiveView] = useState('overview'); // 'overview' | 'map'
  const [subView, setSubView] = useState('dashboard'); // 'dashboard' | 'national-architecture'

  // Auth modal state
  const [authModalOpen, setAuthModalOpen] = useState(false);
  const [authModalMode, setAuthModalMode] = useState('login'); // 'login' | 'signup'
  const [authModalRole, setAuthModalRole] = useState('grid-operator');

  // Synchronize active role with logged-in user role
  useEffect(() => {
    if (user?.role) {
      const normalized = user.role.toLowerCase().replace('_', '-');
      setActiveRole(normalized);
    }
  }, [user]);

  const refreshHealth = async () => {
    const data = await checkBackendHealth();
    setBackendHealth(data);
  };

  useEffect(() => {
    refreshHealth();
    const interval = setInterval(refreshHealth, 30000);
    return () => clearInterval(interval);
  }, []);

  const handleOpenAuth = (mode = 'login', role = 'grid-operator') => {
    setAuthModalMode(mode);
    setAuthModalRole(role);
    setAuthModalOpen(true);
  };

  const handleRoleChange = (roleId) => {
    setActiveRole(roleId);
    if (user) {
      setTemporaryRole(roleId);
    }
  };

  // Render role-specific operational dashboard
  const renderRoleDashboard = () => {
    switch (activeRole) {
      case 'grid-operator':
        return <GridOperatorDashboard onOpenMap={() => setActiveView('map')} user={user} />;
      case 'utility':
        return <UtilityDashboard onOpenMap={() => setActiveView('map')} user={user} />;
      case 'plant-owner':
        return <PlantOwnerDashboard onOpenMap={() => setActiveView('map')} user={user} />;
      case 'energy-trader':
        return <EnergyTraderDashboard onOpenMap={() => setActiveView('map')} user={user} />;
      default:
        return <GridOperatorDashboard onOpenMap={() => setActiveView('map')} user={user} />;
    }
  };

  return (
    <div className="min-h-screen bg-slate-50 text-slate-900 flex flex-col antialiased selection:bg-emerald-100 selection:text-emerald-900">
      {/* Top Enterprise Navigation */}
      <Navbar
        backendStatus={backendHealth?.status || 'offline'}
        activeRole={activeRole}
        activeView={activeView}
        onSelectRole={handleRoleChange}
        onSelectView={(viewId) => setActiveView(viewId)}
        onRefreshHealth={refreshHealth}
        onOpenAuthModal={handleOpenAuth}
      />

      {/* Main Operations Container */}
      <main className="flex-1 max-w-7xl w-full mx-auto px-4 sm:px-6 lg:px-8 py-4 sm:py-6">
        {activeView === 'map' ? (
          <MapViewPage onSwitchToOverview={() => setActiveView('overview')} />
        ) : (
          <div className="space-y-6">
            
            {/* Authenticated Mode Banner / Sub-navigation */}
            {isAuthenticated ? (
              <div className="bg-white rounded-2xl border border-slate-200/80 p-3 sm:p-4 shadow-xs flex flex-col sm:flex-row sm:items-center justify-between gap-3">
                <div className="flex items-center gap-2.5">
                  <div className="w-8 h-8 rounded-xl bg-emerald-100 text-emerald-800 flex items-center justify-center font-bold text-xs">
                    <UserCheck className="w-4 h-4 text-emerald-700" />
                  </div>
                  <div>
                    <div className="flex items-center gap-2">
                      <span className="text-xs font-bold text-slate-900">
                        Active Console: <span className="text-emerald-700 capitalize">{activeRole.replace('-', ' ')}</span>
                      </span>
                      <span className="px-2 py-0.5 rounded-full bg-emerald-50 text-emerald-800 border border-emerald-200 text-[10px] font-semibold">
                        JWT Authenticated
                      </span>
                    </div>
                    <p className="text-[11px] text-slate-500">
                      Logged in as <strong>{user?.full_name}</strong> • {user?.organization || 'Energy Enterprise'}
                    </p>
                  </div>
                </div>

                {/* Switch between Role Specific Dashboard and National Architecture Overview */}
                <div className="flex items-center bg-slate-100 p-1 rounded-xl border border-slate-200 text-xs self-start sm:self-auto">
                  <button
                    onClick={() => setSubView('dashboard')}
                    className={`px-3 py-1.5 font-bold rounded-lg transition-all ${
                      subView === 'dashboard'
                        ? 'bg-white text-emerald-800 shadow-xs'
                        : 'text-slate-600 hover:text-slate-900'
                    }`}
                  >
                    Role Dashboard
                  </button>
                  <button
                    onClick={() => setSubView('national-architecture')}
                    className={`px-3 py-1.5 font-semibold rounded-lg transition-all ${
                      subView === 'national-architecture'
                        ? 'bg-white text-emerald-800 shadow-xs font-bold'
                        : 'text-slate-600 hover:text-slate-900'
                    }`}
                  >
                    National Macro Architecture
                  </button>
                </div>
              </div>
            ) : null}

            {/* Display: Role Dashboard (if logged in and dashboard subview) OR Landing Page */}
            {isAuthenticated && subView === 'dashboard' ? (
              renderRoleDashboard()
            ) : (
              <LandingPage
                activeRole={activeRole}
                onSelectRole={handleRoleChange}
                onOpenMap={() => setActiveView('map')}
                backendHealth={backendHealth}
                onOpenAuthModal={handleOpenAuth}
              />
            )}
          </div>
        )}
      </main>

      {/* Enterprise System Telemetry & Citations Footer */}
      <Footer />

      {/* Auth Modal for Sign In and Role-Based Registration */}
      <AuthModal
        isOpen={authModalOpen}
        onClose={() => setAuthModalOpen(false)}
        initialMode={authModalMode}
        initialRole={authModalRole}
      />
    </div>
  );
}

export default function App() {
  return (
    <AuthProvider>
      <AppContent />
    </AuthProvider>
  );
}
