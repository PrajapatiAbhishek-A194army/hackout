import React from 'react';
import { ShieldCheck, Cpu, Database, CloudSun } from 'lucide-react';

export default function Footer() {
  return (
    <footer className="bg-white border-t border-slate-200 mt-auto text-xs text-slate-500 py-10">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="grid grid-cols-1 md:grid-cols-4 gap-8 mb-8">
          
          {/* Col 1: Platform Overview */}
          <div className="md:col-span-2">
            <div className="flex items-center gap-2 mb-2">
              <span className="font-bold text-slate-900 text-sm">
                Renewable<span className="text-emerald-600">AI</span> Platform
              </span>
              <span className="px-2 py-0.5 rounded text-[10px] font-semibold bg-emerald-50 text-emerald-800 border border-emerald-200">
                Decision Support MVP
              </span>
            </div>
            <p className="text-slate-500 leading-relaxed text-xs max-w-lg">
              Engineered for the <strong>HackOut Renewable Energy Challenge</strong>. Converts live weather forecasts,
              historical generation records, and plant metadata into reliable 24–72h hourly generation forecasts, 
              risk alerts, and actionable grid dispatch recommendations.
            </p>
          </div>

          {/* Col 2: Data Pipeline Sources */}
          <div>
            <span className="font-semibold text-slate-900 block mb-2 text-xs uppercase tracking-wider">
              Data Pipeline Feeds
            </span>
            <ul className="space-y-1.5 text-xs text-slate-600">
              <li className="flex items-center gap-1.5">
                <CloudSun className="w-3.5 h-3.5 text-emerald-600" />
                <span>Open-Meteo (Live Forecasts)</span>
              </li>
              <li className="flex items-center gap-1.5">
                <Database className="w-3.5 h-3.5 text-emerald-600" />
                <span>NASA POWER (Solar History)</span>
              </li>
              <li className="flex items-center gap-1.5">
                <Cpu className="w-3.5 h-3.5 text-emerald-600" />
                <span>MNRE / CEA (Plant Metadata)</span>
              </li>
              <li className="flex items-center gap-1.5">
                <ShieldCheck className="w-3.5 h-3.5 text-emerald-600" />
                <span>NREL Public Generation Benchmarks</span>
              </li>
            </ul>
          </div>

          {/* Col 3: Core Architecture Stack */}
          <div>
            <span className="font-semibold text-slate-900 block mb-2 text-xs uppercase tracking-wider">
              Technology Stack
            </span>
            <ul className="space-y-1 text-xs text-slate-600">
              <li>Python 3.10 • FastAPI REST API</li>
              <li>SQLAlchemy 2.0 • PostgreSQL • Alembic</li>
              <li>Dual XGBoost Regressors (Solar & Wind)</li>
              <li>React 18 • Vite • Tailwind CSS • Recharts</li>
              <li>React Leaflet Geospatial Layer</li>
            </ul>
          </div>

        </div>

        {/* Bottom Bar */}
        <div className="pt-6 border-t border-slate-100 flex flex-col sm:flex-row items-center justify-between gap-3 text-[11px] text-slate-400">
          <div>
            © {new Date().getFullYear()} RenewableAI Intelligence Platform. Built for Indian Power Grid Stability.
          </div>
          <div className="flex items-center gap-4">
            <span>Forecast Horizon: 24h • 48h • 72h</span>
            <span>•</span>
            <span>Hierarchy: Farm → Region → State → National</span>
          </div>
        </div>
      </div>
    </footer>
  );
}
