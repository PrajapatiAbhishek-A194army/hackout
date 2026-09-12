import React from 'react';
import { 
  Zap, 
  Activity, 
  BookOpen, 
  Server, 
  ShieldCheck,
  ChevronRight,
  Compass,
  LayoutDashboard
} from 'lucide-react';
import Badge from './Badge';

export default function Navbar({ 
  backendStatus = 'online', 
  activeRole = 'grid-operator', 
  activeView = 'overview',
  onSelectRole,
  onSelectView,
  onRefreshHealth 
}) {
  const roles = [
    { id: 'grid-operator', label: 'Grid Operator' },
    { id: 'plant-owner', label: 'Plant Owner' },
    { id: 'utility', label: 'Utility Company' },
    { id: 'energy-trader', label: 'Energy Trader' }
  ];

  return (
    <header className="bg-white/95 backdrop-blur-md border-b border-slate-200/90 sticky top-0 z-40 shadow-xs">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="h-16 flex items-center justify-between gap-4">
          
          {/* Brand Logo & View Selector */}
          <div className="flex items-center gap-4 shrink-0">
            <div 
              onClick={() => onSelectView && onSelectView('overview')}
              className="flex items-center gap-3 cursor-pointer group"
            >
              <div className="w-10 h-10 rounded-xl bg-gradient-to-br from-emerald-600 to-teal-700 flex items-center justify-center text-white shadow-emerald-glow shadow-sm group-hover:scale-105 transition-transform">
                <Zap className="w-5 h-5" />
              </div>
              <div>
                <div className="flex items-center gap-2">
                  <span className="text-lg font-bold tracking-tight text-slate-900">
                    Renewable<span className="text-emerald-600">AI</span>
                  </span>
                  <span className="hidden sm:inline-flex items-center px-2 py-0.5 rounded text-[11px] font-semibold bg-emerald-50 text-emerald-800 border border-emerald-200">
                    National Operations
                  </span>
                </div>
                <p className="text-[11px] text-slate-400 hidden sm:block">
                  AI Generation Forecasting & Decision Engine
                </p>
              </div>
            </div>

            {/* View Mode Switcher */}
            <div className="hidden md:flex items-center bg-slate-100 p-1 rounded-xl border border-slate-200 text-xs">
              <button
                onClick={() => onSelectView && onSelectView('overview')}
                className={`flex items-center gap-1.5 px-3 py-1.5 font-semibold rounded-lg transition-all ${
                  activeView === 'overview'
                    ? 'bg-white text-emerald-800 shadow-xs border border-slate-200/80 font-bold'
                    : 'text-slate-600 hover:text-slate-900'
                }`}
              >
                <LayoutDashboard className="w-3.5 h-3.5" />
                <span>Overview</span>
              </button>
              <button
                onClick={() => onSelectView && onSelectView('map')}
                className={`flex items-center gap-1.5 px-3 py-1.5 font-semibold rounded-lg transition-all ${
                  activeView === 'map'
                    ? 'bg-white text-emerald-800 shadow-xs border border-slate-200/80 font-bold'
                    : 'text-slate-600 hover:text-slate-900'
                }`}
              >
                <Compass className="w-3.5 h-3.5 text-emerald-600" />
                <span>Spatial Map</span>
                <span className="h-1.5 w-1.5 rounded-full bg-emerald-500 animate-pulse" />
              </button>
            </div>
          </div>

          {/* Center: Operational Role Selector (Active on Overview) */}
          <nav className="hidden lg:flex items-center bg-slate-100/90 p-1 rounded-xl border border-slate-200/70 text-xs">
            {roles.map((role) => {
              const active = activeRole === role.id;
              return (
                <button
                  key={role.id}
                  onClick={() => {
                    if (onSelectRole) onSelectRole(role.id);
                    if (onSelectView && activeView !== 'overview') onSelectView('overview');
                  }}
                  className={`px-3 py-1.5 font-semibold rounded-lg transition-all duration-150 ${
                    active && activeView === 'overview'
                      ? 'bg-white text-emerald-800 shadow-xs border border-slate-200/80 font-bold' 
                      : 'text-slate-600 hover:text-slate-900 hover:bg-slate-200/50'
                  }`}
                >
                  {role.label}
                </button>
              );
            })}
          </nav>

          {/* Right Action Items: Backend Health Status & API Link */}
          <div className="flex items-center gap-2.5 shrink-0">
            {/* Mobile View Switcher */}
            <div className="md:hidden flex items-center">
              <button
                onClick={() => onSelectView && onSelectView(activeView === 'overview' ? 'map' : 'overview')}
                className="flex items-center gap-1 px-2.5 py-1 text-xs font-semibold bg-slate-100 text-slate-800 rounded-lg border border-slate-200"
              >
                {activeView === 'overview' ? <Compass className="w-3.5 h-3.5 text-emerald-600" /> : <LayoutDashboard className="w-3.5 h-3.5 text-emerald-600" />}
                <span>{activeView === 'overview' ? 'Map' : 'Console'}</span>
              </button>
            </div>

            {/* Backend connection pill */}
            <div 
              onClick={onRefreshHealth}
              title="Click to re-probe backend status"
              className="cursor-pointer transition-transform active:scale-95"
            >
              <Badge 
                variant={backendStatus === 'online' ? 'normal' : 'warning'} 
                dot 
                pulse={backendStatus === 'online'}
              >
                <Server className="w-3 h-3 text-emerald-600" />
                <span className="hidden sm:inline">Backend:</span>
                <span className="capitalize">{backendStatus}</span>
              </Badge>
            </div>

            {/* Swagger API docs link */}
            <a
              href="http://127.0.0.1:8000/docs"
              target="_blank"
              rel="noopener noreferrer"
              className="inline-flex items-center gap-1.5 px-3 py-1.5 text-xs font-semibold text-slate-700 bg-white border border-slate-200 rounded-lg hover:bg-slate-50 hover:border-slate-300 transition-colors shadow-xs"
            >
              <BookOpen className="w-3.5 h-3.5 text-slate-500" />
              <span className="hidden md:inline">API Docs</span>
            </a>
          </div>

        </div>
      </div>
    </header>
  );
}
