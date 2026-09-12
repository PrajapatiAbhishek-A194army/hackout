import React from 'react';
import { ShieldCheck, Cpu, Database, CloudSun, Activity, Radio, ExternalLink } from 'lucide-react';

export default function Footer() {
  return (
    <footer className="bg-white border-t border-slate-200 mt-auto text-xs text-slate-500 py-10">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="grid grid-cols-1 md:grid-cols-4 gap-8 mb-8">
          
          {/* Col 1: Platform Overview */}
          <div className="md:col-span-2">
            <div className="flex items-center gap-2 mb-2">
              <span className="font-bold text-slate-900 text-sm tracking-tight">
                Renewable<span className="text-emerald-600">AI</span> Intelligence
              </span>
              <span className="px-2 py-0.5 rounded text-[10px] font-semibold bg-emerald-50 text-emerald-800 border border-emerald-200">
                Operational Grid Engine
              </span>
            </div>
            <p className="text-slate-500 leading-relaxed text-xs max-w-lg">
              National renewable generation forecasting and balancing decision engine. Translates meteorological 
              data, farm telemetry, and historical benchmarks into high-confidence 24–72h generation forecasts, 
              duck curve ramp alerts, and actionable grid dispatch directives.
            </p>
          </div>

          {/* Col 2: Stakeholder Solutions */}
          <div>
            <span className="font-semibold text-slate-900 block mb-2 text-xs uppercase tracking-wider">
              Operational Solutions
            </span>
            <ul className="space-y-1.5 text-xs text-slate-600">
              <li className="hover:text-emerald-700 transition-colors cursor-pointer">
                National & State Grid Operators (RLDC / SLDC)
              </li>
              <li className="hover:text-emerald-700 transition-colors cursor-pointer">
                Distribution Utilities (DISCOM Procurement)
              </li>
              <li className="hover:text-emerald-700 transition-colors cursor-pointer">
                Renewable Asset Owners (Solar & Wind IPPs)
              </li>
              <li className="hover:text-emerald-700 transition-colors cursor-pointer">
                Power Market Analysts & Energy Traders
              </li>
            </ul>
          </div>

          {/* Col 3: Compliance & Grid Reliability */}
          <div>
            <span className="font-semibold text-slate-900 block mb-2 text-xs uppercase tracking-wider">
              Grid Reliability Standards
            </span>
            <ul className="space-y-1.5 text-xs text-slate-600">
              <li className="flex items-center gap-1.5">
                <ShieldCheck className="w-3.5 h-3.5 text-emerald-600" />
                <span>Indian Electricity Grid Code (IEGC)</span>
              </li>
              <li className="flex items-center gap-1.5">
                <Activity className="w-3.5 h-3.5 text-emerald-600" />
                <span>50.00 Hz Frequency Balancing Band</span>
              </li>
              <li className="flex items-center gap-1.5">
                <Radio className="w-3.5 h-3.5 text-emerald-600" />
                <span>CERC DSM Deviation Protection</span>
              </li>
              <li className="flex items-center gap-1.5">
                <Database className="w-3.5 h-3.5 text-emerald-600" />
                <span>SCADA & IoT Telemetry Ready</span>
              </li>
            </ul>
          </div>

        </div>

        {/* Bottom Bar */}
        <div className="pt-6 border-t border-slate-100 flex flex-col sm:flex-row items-center justify-between gap-3 text-[11px] text-slate-400">
          <div>
            © {new Date().getFullYear()} RenewableAI Decision Systems. Designed for Grid Reliability & Clean Energy Dispatch.
          </div>
          <div className="flex items-center gap-4">
            <span>Forecast Horizons: 24h • 48h • 72h</span>
            <span>•</span>
            <span>Spatial Rollup: Farm → Region → State → National</span>
          </div>
        </div>
      </div>
    </footer>
  );
}
