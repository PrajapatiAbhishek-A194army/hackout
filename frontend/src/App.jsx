import React, { useState, useEffect } from 'react';
import { Navbar, Footer } from './components';
import { LandingPage } from './pages';
import { checkBackendHealth } from './services/api';

export default function App() {
  const [backendHealth, setBackendHealth] = useState({ status: 'connecting', database: 'probing' });
  const [activeRole, setActiveRole] = useState('grid-operator');

  const refreshHealth = async () => {
    const data = await checkBackendHealth();
    setBackendHealth(data);
  };

  useEffect(() => {
    refreshHealth();
    // Poll health every 30 seconds
    const interval = setInterval(refreshHealth, 30000);
    return () => clearInterval(interval);
  }, []);

  return (
    <div className="min-h-screen bg-slate-50 text-slate-900 flex flex-col antialiased selection:bg-emerald-100 selection:text-emerald-900">
      {/* Top Enterprise Navigation */}
      <Navbar
        backendStatus={backendHealth?.status || 'offline'}
        activeRole={activeRole}
        onSelectRole={(roleId) => setActiveRole(roleId)}
        onRefreshHealth={refreshHealth}
      />

      {/* Main Operations Container */}
      <main className="flex-1 max-w-7xl w-full mx-auto px-4 sm:px-6 lg:px-8">
        <LandingPage
          activeRole={activeRole}
          onSelectRole={(roleId) => setActiveRole(roleId)}
          backendHealth={backendHealth}
        />
      </main>

      {/* Enterprise System Telemetry & Citations Footer */}
      <Footer />
    </div>
  );
}
