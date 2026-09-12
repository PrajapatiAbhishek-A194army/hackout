import React from 'react';
import { 
  Filter, 
  Layers, 
  Sun, 
  Wind, 
  Zap, 
  ShieldAlert, 
  CheckCircle2, 
  AlertTriangle, 
  Flame, 
  CloudSun, 
  RotateCcw,
  Compass
} from 'lucide-react';

export default function MapFilterBar({
  filters,
  onFilterChange,
  onResetFilters,
  regions = [],
  stats = { totalCount: 0, totalCapacity: 0, liveOutput: 0, alertCount: 0 }
}) {
  return (
    <div className="bg-white/95 backdrop-blur-md rounded-2xl border border-slate-200/90 shadow-sm p-4 space-y-4">
      
      {/* Top Stat Ribbon */}
      <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 pb-3 border-b border-slate-200/80 text-xs">
        <div className="bg-slate-50 rounded-xl p-2.5 border border-slate-200/70">
          <span className="text-slate-500 font-medium block text-[11px]">Filtered Assets</span>
          <span className="text-base font-bold text-slate-900">{stats.totalCount} Plants</span>
        </div>
        <div className="bg-emerald-50/70 rounded-xl p-2.5 border border-emerald-200/70">
          <span className="text-emerald-700 font-medium block text-[11px]">Total Capacity</span>
          <span className="text-base font-bold text-emerald-900">
            {stats.totalCapacity ? Number(stats.totalCapacity).toLocaleString() : '0'} MW
          </span>
        </div>
        <div className="bg-teal-50/70 rounded-xl p-2.5 border border-teal-200/70">
          <span className="text-teal-700 font-medium block text-[11px]">Live Generation</span>
          <span className="text-base font-bold text-teal-900">
            {stats.liveOutput ? Number(stats.liveOutput).toLocaleString() : '0'} MW
          </span>
        </div>
        <div className="bg-rose-50/70 rounded-xl p-2.5 border border-rose-200/70">
          <span className="text-rose-700 font-medium block text-[11px]">Active Risk Alerts</span>
          <span className="text-base font-bold text-rose-900 flex items-center gap-1.5">
            {stats.alertCount > 0 ? (
              <>
                <span className="h-2 w-2 rounded-full bg-rose-500 animate-ping" />
                {stats.alertCount} Events
              </>
            ) : (
              '0 Alerts'
            )}
          </span>
        </div>
      </div>

      {/* Filter Row 1: Type, Status, Region */}
      <div className="flex flex-wrap items-center justify-between gap-3 text-xs">
        
        {/* Technology Type Filter */}
        <div className="flex items-center gap-1 bg-slate-100 p-1 rounded-xl border border-slate-200">
          <button
            onClick={() => onFilterChange('type', 'all')}
            className={`px-2.5 py-1.5 rounded-lg font-medium transition-all ${
              filters.type === 'all' 
                ? 'bg-white text-slate-900 shadow-xs font-bold' 
                : 'text-slate-600 hover:text-slate-900'
            }`}
          >
            All Tech
          </button>
          <button
            onClick={() => onFilterChange('type', 'solar')}
            className={`flex items-center gap-1 px-2.5 py-1.5 rounded-lg font-medium transition-all ${
              filters.type === 'solar' 
                ? 'bg-white text-amber-800 shadow-xs font-bold border border-amber-200/80' 
                : 'text-slate-600 hover:text-slate-900'
            }`}
          >
            <Sun className="w-3.5 h-3.5 text-amber-500" />
            Solar
          </button>
          <button
            onClick={() => onFilterChange('type', 'wind')}
            className={`flex items-center gap-1 px-2.5 py-1.5 rounded-lg font-medium transition-all ${
              filters.type === 'wind' 
                ? 'bg-white text-teal-800 shadow-xs font-bold border border-teal-200/80' 
                : 'text-slate-600 hover:text-slate-900'
            }`}
          >
            <Wind className="w-3.5 h-3.5 text-teal-500" />
            Wind
          </button>
          <button
            onClick={() => onFilterChange('type', 'hybrid')}
            className={`flex items-center gap-1 px-2.5 py-1.5 rounded-lg font-medium transition-all ${
              filters.type === 'hybrid' 
                ? 'bg-white text-purple-800 shadow-xs font-bold border border-purple-200/80' 
                : 'text-slate-600 hover:text-slate-900'
            }`}
          >
            <Zap className="w-3.5 h-3.5 text-purple-500" />
            Hybrid
          </button>
        </div>

        {/* Operational Status Filter */}
        <div className="flex items-center gap-1 bg-slate-100 p-1 rounded-xl border border-slate-200">
          <button
            onClick={() => onFilterChange('status', 'all')}
            className={`px-2.5 py-1.5 rounded-lg font-medium transition-all ${
              filters.status === 'all' 
                ? 'bg-white text-slate-900 shadow-xs font-bold' 
                : 'text-slate-600 hover:text-slate-900'
            }`}
          >
            All Status
          </button>
          <button
            onClick={() => onFilterChange('status', 'normal')}
            className={`flex items-center gap-1 px-2.5 py-1.5 rounded-lg font-medium transition-all ${
              filters.status === 'normal' 
                ? 'bg-white text-emerald-800 shadow-xs font-bold border border-emerald-200' 
                : 'text-slate-600 hover:text-slate-900'
            }`}
          >
            <span className="w-2 h-2 rounded-full bg-emerald-500" />
            Normal
          </button>
          <button
            onClick={() => onFilterChange('status', 'warning')}
            className={`flex items-center gap-1 px-2.5 py-1.5 rounded-lg font-medium transition-all ${
              filters.status === 'warning' 
                ? 'bg-white text-amber-800 shadow-xs font-bold border border-amber-200' 
                : 'text-slate-600 hover:text-slate-900'
            }`}
          >
            <span className="w-2 h-2 rounded-full bg-amber-500" />
            Warning
          </button>
          <button
            onClick={() => onFilterChange('status', 'critical')}
            className={`flex items-center gap-1 px-2.5 py-1.5 rounded-lg font-medium transition-all ${
              filters.status === 'critical' 
                ? 'bg-white text-rose-800 shadow-xs font-bold border border-rose-200' 
                : 'text-slate-600 hover:text-slate-900'
            }`}
          >
            <span className="w-2 h-2 rounded-full bg-rose-500" />
            Critical
          </button>
        </div>

        {/* Regional Grid Filter */}
        <div className="flex items-center gap-2">
          <span className="text-slate-500 font-medium hidden sm:inline">Region:</span>
          <select
            value={filters.region}
            onChange={(e) => onFilterChange('region', e.target.value)}
            className="px-3 py-1.5 bg-slate-50 border border-slate-200 rounded-xl text-slate-800 font-medium focus:ring-2 focus:ring-emerald-500/20 focus:border-emerald-500 outline-none"
          >
            <option value="all">All Balancing Regions</option>
            {regions.map((r) => (
              <option key={r.id || r.code} value={r.code || r.name}>
                {r.name} ({r.code})
              </option>
            ))}
          </select>
        </div>

        {/* Reset Filter Button */}
        <button
          onClick={onResetFilters}
          className="flex items-center gap-1 px-2.5 py-1.5 rounded-xl text-slate-500 hover:text-slate-800 hover:bg-slate-100 transition-colors"
          title="Reset all filters"
        >
          <RotateCcw className="w-3.5 h-3.5" />
          <span className="hidden md:inline">Reset</span>
        </button>

      </div>

      {/* Filter Row 2: Layer Toggles & Capacity Threshold */}
      <div className="flex flex-wrap items-center justify-between gap-3 pt-2 border-t border-slate-100 text-xs">
        
        {/* Layer Toggles */}
        <div className="flex items-center gap-2 flex-wrap">
          <span className="text-slate-400 font-medium flex items-center gap-1">
            <Layers className="w-3.5 h-3.5" />
            Layers:
          </span>

          <label className="flex items-center gap-1.5 cursor-pointer select-none px-2.5 py-1 rounded-lg border border-slate-200 bg-white hover:bg-slate-50">
            <input
              type="checkbox"
              checked={filters.showHeatmap}
              onChange={(e) => onFilterChange('showHeatmap', e.target.checked)}
              className="w-3.5 h-3.5 rounded text-emerald-600 focus:ring-emerald-500"
            />
            <Flame className="w-3.5 h-3.5 text-amber-500" />
            <span>Capacity Heat</span>
          </label>

          <label className="flex items-center gap-1.5 cursor-pointer select-none px-2.5 py-1 rounded-lg border border-slate-200 bg-white hover:bg-slate-50">
            <input
              type="checkbox"
              checked={filters.showWeather}
              onChange={(e) => onFilterChange('showWeather', e.target.checked)}
              className="w-3.5 h-3.5 rounded text-emerald-600 focus:ring-emerald-500"
            />
            <CloudSun className="w-3.5 h-3.5 text-blue-500" />
            <span>Weather Overlay</span>
          </label>

          <label className="flex items-center gap-1.5 cursor-pointer select-none px-2.5 py-1 rounded-lg border border-slate-200 bg-white hover:bg-slate-50">
            <input
              type="checkbox"
              checked={filters.showRegionalClusters}
              onChange={(e) => onFilterChange('showRegionalClusters', e.target.checked)}
              className="w-3.5 h-3.5 rounded text-emerald-600 focus:ring-emerald-500"
            />
            <Compass className="w-3.5 h-3.5 text-teal-600" />
            <span>Regional Corridors</span>
          </label>
        </div>

        {/* Capacity Slider / Min Filter */}
        <div className="flex items-center gap-2">
          <span className="text-slate-500 font-medium">Min Capacity:</span>
          <span className="font-bold text-slate-800 min-w-[50px]">{filters.minCapacity} MW</span>
          <input
            type="range"
            min="0"
            max="3000"
            step="250"
            value={filters.minCapacity}
            onChange={(e) => onFilterChange('minCapacity', Number(e.target.value))}
            className="w-24 sm:w-32 accent-emerald-600 cursor-pointer"
          />
        </div>

      </div>

    </div>
  );
}
