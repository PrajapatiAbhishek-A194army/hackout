import React, { useState, useEffect } from 'react';
import { 
  Activity, 
  CheckCircle2, 
  Sun, 
  Wind, 
  Zap, 
  Layers, 
  AlertTriangle, 
  ShieldCheck, 
  Server, 
  Cpu, 
  Database,
  ArrowRight,
  TrendingUp,
  RefreshCw
} from 'lucide-react';
import { checkBackendHealth } from './services/api';

export default function App() {
  const [health, setHealth] = useState(null);
  const [loading, setLoading] = useState(true);

  const fetchHealth = async () => {
    setLoading(true);
    const data = await checkBackendHealth();
    setHealth(data);
    setLoading(false);
  };

  useEffect(() => {
    fetchHealth();
  }, []);

  return (
    <div className="min-h-screen bg-slate-50 text-slate-900 flex flex-col">
      {/* Top Enterprise Navigation Header */}
      <header className="bg-white border-b border-slate-200 sticky top-0 z-30 shadow-xs">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 h-16 flex items-center justify-between">
          <div className="flex items-center space-x-3">
            <div className="w-10 h-10 rounded-lg bg-emerald-600 flex items-center justify-center text-white shadow-sm shadow-emerald-200">
              <Zap className="w-6 h-6" />
            </div>
            <div>
              <span className="text-lg font-bold tracking-tight text-slate-900">
                Renewable<span className="text-emerald-600">AI</span>
              </span>
              <span className="hidden sm:inline-block ml-2 px-2 py-0.5 text-xs font-semibold bg-emerald-50 text-emerald-700 border border-emerald-200 rounded-md">
                Operations Console
              </span>
            </div>
          </div>

          <div className="flex items-center space-x-3">
            <button
              onClick={fetchHealth}
              disabled={loading}
              className="inline-flex items-center space-x-1.5 px-3 py-1.5 text-xs font-medium text-slate-600 bg-slate-100 hover:bg-slate-200 rounded-md transition-colors"
            >
              <RefreshCw className={`w-3.5 h-3.5 ${loading ? 'animate-spin' : ''}`} />
              <span>Refresh Status</span>
            </button>
            <div className="flex items-center space-x-2 px-3 py-1.5 bg-emerald-50 border border-emerald-200 rounded-full">
              <span className="relative flex h-2.5 w-2.5">
                <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-emerald-400 opacity-75"></span>
                <span className="relative inline-flex rounded-full h-2.5 w-2.5 bg-emerald-500"></span>
              </span>
              <span className="text-xs font-medium text-emerald-800">
                Phase 1: Foundation Ready
              </span>
            </div>
          </div>
        </div>
      </header>

      {/* Main Content */}
      <main className="flex-1 max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8 w-full">
        {/* Banner Section */}
        <div className="bg-gradient-to-r from-emerald-800 via-emerald-700 to-teal-800 rounded-2xl p-8 text-white shadow-card mb-8">
          <div className="max-w-3xl">
            <div className="inline-flex items-center space-x-2 px-3 py-1 rounded-full bg-emerald-600/50 border border-emerald-400/30 text-emerald-100 text-xs font-medium mb-4">
              <ShieldCheck className="w-3.5 h-3.5" />
              <span>HackOut Renewable Energy Challenge</span>
            </div>
            <h1 className="text-3xl sm:text-4xl font-extrabold tracking-tight">
              AI-Powered Renewable Generation Forecasting Platform
            </h1>
            <p className="mt-3 text-emerald-100 text-sm sm:text-base leading-relaxed">
              Transforming Weather + Historical Generation + Plant Metadata into high-resolution 24–72h 
              forecasts, multi-level operational risk alerts, and explainable grid balancing recommendations.
            </p>
          </div>
        </div>

        {/* Foundation Status & Architecture Grid */}
        <div className="grid grid-cols-1 md:grid-cols-3 gap-6 mb-8">
          {/* Backend Status Card */}
          <div className="bg-white rounded-xl border border-slate-200 p-6 shadow-card hover:border-emerald-300 transition-colors">
            <div className="flex items-center justify-between mb-4">
              <div className="w-10 h-10 rounded-lg bg-slate-100 flex items-center justify-center text-slate-700">
                <Server className="w-5 h-5 text-emerald-600" />
              </div>
              <span className={`px-2.5 py-1 text-xs font-medium rounded-full ${
                health?.status === 'online' || health?.status === 'healthy' 
                  ? 'bg-emerald-100 text-emerald-800' 
                  : 'bg-amber-100 text-amber-800'
              }`}>
                {health?.status || 'Connecting...'}
              </span>
            </div>
            <h3 className="text-base font-semibold text-slate-900">FastAPI Backend</h3>
            <p className="text-xs text-slate-500 mt-1">Python 3.10 • REST API v1 • CORS Enabled</p>
            <div className="mt-4 pt-4 border-t border-slate-100 space-y-2 text-xs">
              <div className="flex justify-between text-slate-600">
                <span>Database engine:</span>
                <span className="font-mono font-medium text-slate-900">{health?.database || 'SQLAlchemy Engine'}</span>
              </div>
              <div className="flex justify-between text-slate-600">
                <span>API Prefix:</span>
                <span className="font-mono text-slate-900">/api/v1</span>
              </div>
            </div>
          </div>

          {/* Machine Learning Pipeline Card */}
          <div className="bg-white rounded-xl border border-slate-200 p-6 shadow-card hover:border-emerald-300 transition-colors">
            <div className="flex items-center justify-between mb-4">
              <div className="w-10 h-10 rounded-lg bg-slate-100 flex items-center justify-center text-slate-700">
                <Cpu className="w-5 h-5 text-emerald-600" />
              </div>
              <span className="px-2.5 py-1 text-xs font-medium rounded-full bg-blue-50 text-blue-700 border border-blue-200">
                Architecture Ready
              </span>
            </div>
            <h3 className="text-base font-semibold text-slate-900">Dual XGBoost Core</h3>
            <p className="text-xs text-slate-500 mt-1">Independent Solar & Wind Farm Regressors</p>
            <div className="mt-4 pt-4 border-t border-slate-100 space-y-2 text-xs">
              <div className="flex justify-between text-slate-600">
                <span>Forecast Horizons:</span>
                <span className="font-medium text-slate-900">24h • 48h • 72h</span>
              </div>
              <div className="flex justify-between text-slate-600">
                <span>Aggregation:</span>
                <span className="font-medium text-slate-900">Farm → Region → State → National</span>
              </div>
            </div>
          </div>

          {/* Data Strategy Card */}
          <div className="bg-white rounded-xl border border-slate-200 p-6 shadow-card hover:border-emerald-300 transition-colors">
            <div className="flex items-center justify-between mb-4">
              <div className="w-10 h-10 rounded-lg bg-slate-100 flex items-center justify-center text-slate-700">
                <Database className="w-5 h-5 text-emerald-600" />
              </div>
              <span className="px-2.5 py-1 text-xs font-medium rounded-full bg-emerald-50 text-emerald-700 border border-emerald-200">
                Connected
              </span>
            </div>
            <h3 className="text-base font-semibold text-slate-900">Public & Live Data Pipeline</h3>
            <p className="text-xs text-slate-500 mt-1">Open-Meteo • NASA POWER • MNRE / CEA</p>
            <div className="mt-4 pt-4 border-t border-slate-100 space-y-2 text-xs">
              <div className="flex justify-between text-slate-600">
                <span>Live Weather:</span>
                <span className="font-medium text-slate-900">Automated Coordinate Fetch</span>
              </div>
              <div className="flex justify-between text-slate-600">
                <span>SCADA Ready:</span>
                <span className="font-medium text-slate-900">Pluggable IoT Ingestion</span>
              </div>
            </div>
          </div>
        </div>

        {/* 4-Tier Forecast Hierarchy Overview */}
        <div className="bg-white rounded-xl border border-slate-200 p-6 shadow-card mb-8">
          <div className="flex items-center justify-between mb-6">
            <div>
              <h2 className="text-lg font-bold text-slate-900">Forecast Hierarchy & Aggregation Workflow</h2>
              <p className="text-xs text-slate-500 mt-0.5">
                Mathematical upward aggregation preserving plant-level physical accuracy
              </p>
            </div>
            <span className="text-xs font-semibold px-2.5 py-1 bg-slate-100 text-slate-700 rounded-md">
              Core Design
            </span>
          </div>

          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
            <div className="p-4 rounded-lg bg-slate-50 border border-slate-200/80">
              <div className="flex items-center space-x-2 text-emerald-700 font-semibold text-sm mb-1">
                <Sun className="w-4 h-4" />
                <span>1. Farm Level</span>
              </div>
              <p className="text-xs text-slate-600">
                XGBoost predicts hourly MW using site coordinates, weather drivers & capacity.
              </p>
            </div>

            <div className="p-4 rounded-lg bg-slate-50 border border-slate-200/80">
              <div className="flex items-center space-x-2 text-emerald-700 font-semibold text-sm mb-1">
                <Layers className="w-4 h-4" />
                <span>2. Region Level</span>
              </div>
              <p className="text-xs text-slate-600">
                Summed local farm predictions for local distribution and feeder balancing.
              </p>
            </div>

            <div className="p-4 rounded-lg bg-slate-50 border border-slate-200/80">
              <div className="flex items-center space-x-2 text-emerald-700 font-semibold text-sm mb-1">
                <TrendingUp className="w-4 h-4" />
                <span>3. State Level</span>
              </div>
              <p className="text-xs text-slate-600">
                State aggregate forecasts enabling SLDC planning and risk prioritization.
              </p>
            </div>

            <div className="p-4 rounded-lg bg-slate-50 border border-slate-200/80">
              <div className="flex items-center space-x-2 text-emerald-700 font-semibold text-sm mb-1">
                <Zap className="w-4 h-4" />
                <span>4. National Level</span>
              </div>
              <p className="text-xs text-slate-600">
                Macro grid overview for national transmission planning & inter-state scheduling.
              </p>
            </div>
          </div>
        </div>

        {/* Operational Roles Preview */}
        <div className="bg-white rounded-xl border border-slate-200 p-6 shadow-card">
          <h2 className="text-lg font-bold text-slate-900 mb-4">Operational Consoles Supported</h2>
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
            <div className="p-4 rounded-lg border border-slate-200 hover:border-emerald-400 transition-colors">
              <span className="text-xs font-semibold text-emerald-700 uppercase tracking-wider">Role 1</span>
              <h4 className="font-semibold text-slate-900 text-sm mt-1">Grid Operator</h4>
              <p className="text-xs text-slate-500 mt-1">National overview, state risk timeline, balancing alerts.</p>
            </div>
            <div className="p-4 rounded-lg border border-slate-200 hover:border-emerald-400 transition-colors">
              <span className="text-xs font-semibold text-emerald-700 uppercase tracking-wider">Role 2</span>
              <h4 className="font-semibold text-slate-900 text-sm mt-1">Plant Owner</h4>
              <p className="text-xs text-slate-500 mt-1">Farm forecast curve, utilization, maintenance windows.</p>
            </div>
            <div className="p-4 rounded-lg border border-slate-200 hover:border-emerald-400 transition-colors">
              <span className="text-xs font-semibold text-emerald-700 uppercase tracking-wider">Role 3</span>
              <h4 className="font-semibold text-slate-900 text-sm mt-1">Utility Company</h4>
              <p className="text-xs text-slate-500 mt-1">Renewable supply vs expected demand, procurement planning.</p>
            </div>
            <div className="p-4 rounded-lg border border-slate-200 hover:border-emerald-400 transition-colors">
              <span className="text-xs font-semibold text-emerald-700 uppercase tracking-wider">Role 4</span>
              <h4 className="font-semibold text-slate-900 text-sm mt-1">Energy Trader</h4>
              <p className="text-xs text-slate-500 mt-1">Regional supply signals, high/low generation arbitrage windows.</p>
            </div>
          </div>
        </div>
      </main>

      {/* Footer */}
      <footer className="bg-white border-t border-slate-200 py-4 mt-auto">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 flex flex-col sm:flex-row items-center justify-between text-xs text-slate-500">
          <div>
            AI-Powered Renewable Generation Forecasting Platform • Built for HackOut Challenge
          </div>
          <div className="mt-2 sm:mt-0">
            Phase 1 Foundation: React + Vite + Tailwind | FastAPI + SQLAlchemy + Alembic
          </div>
        </div>
      </footer>
    </div>
  );
}
