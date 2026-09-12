import React from 'react';
import { 
  X, 
  Sun, 
  Wind, 
  Zap, 
  BatteryCharging, 
  Gauge, 
  Thermometer, 
  Compass, 
  CloudRain, 
  ShieldAlert, 
  ArrowRight,
  TrendingUp,
  Activity,
  CheckCircle2,
  Calendar
} from 'lucide-react';
import { ResponsiveContainer, AreaChart, Area, XAxis, YAxis, Tooltip } from 'recharts';

export default function PlantDrawer({
  plant,
  telemetry,
  forecastData = [],
  alerts = [],
  onClose,
  onInspectForecast
}) {
  if (!plant) return null;

  const techColor = 
    plant.plant_type === 'solar' ? 'amber' :
    plant.plant_type === 'wind' ? 'teal' : 'purple';

  const status = telemetry?.operational_status || plant.status || 'NORMAL';
  const isAlert = status === 'WARNING' || status === 'CRITICAL' || status === 'CURTAILED';
  const genMW = telemetry?.current_generation_mw ?? (plant.capacity_mw * 0.72);
  const cuf = telemetry?.capacity_factor_pct ?? Math.round((genMW / plant.capacity_mw) * 100);

  // Generate synthetic 24h curve if forecast points not passed
  const chartPoints = forecastData.length > 0 ? forecastData : Array.from({ length: 24 }, (_, h) => {
    const isDay = h >= 6 && h <= 18;
    const solarFactor = isDay ? Math.sin(((h - 6) / 12) * Math.PI) : 0;
    const windFactor = 0.4 + 0.3 * Math.cos((h / 24) * 2 * Math.PI);
    const ratio = plant.plant_type === 'solar' ? solarFactor : plant.plant_type === 'wind' ? windFactor : (solarFactor * 0.6 + windFactor * 0.4);
    return {
      hour: `${h}:00`,
      predicted_mw: Math.round(plant.capacity_mw * ratio),
      lower_ci: Math.round(plant.capacity_mw * ratio * 0.9),
      upper_ci: Math.round(plant.capacity_mw * ratio * 1.1),
    };
  });

  return (
    <div className="w-full sm:w-96 bg-white/95 backdrop-blur-md border-t sm:border-t-0 sm:border-l border-slate-200 shadow-2xl p-5 flex flex-col h-full max-h-[85vh] sm:max-h-full overflow-y-auto z-30">
      
      {/* Header */}
      <div className="flex items-start justify-between pb-4 border-b border-slate-200">
        <div>
          <div className="flex items-center gap-2 mb-1">
            <span className={`inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-[11px] font-bold uppercase tracking-wider ${
              plant.plant_type === 'solar' ? 'bg-amber-100 text-amber-800' :
              plant.plant_type === 'wind' ? 'bg-teal-100 text-teal-800' : 'bg-purple-100 text-purple-800'
            }`}>
              {plant.plant_type === 'solar' && <Sun className="w-3 h-3" />}
              {plant.plant_type === 'wind' && <Wind className="w-3 h-3" />}
              {plant.plant_type === 'hybrid' && <Zap className="w-3 h-3" />}
              {plant.plant_type}
            </span>
            <span className={`inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-[11px] font-semibold ${
              status === 'NORMAL' ? 'bg-emerald-100 text-emerald-800' :
              status === 'WARNING' ? 'bg-amber-100 text-amber-800' : 'bg-rose-100 text-rose-800'
            }`}>
              <span className={`w-1.5 h-1.5 rounded-full ${
                status === 'NORMAL' ? 'bg-emerald-500' :
                status === 'WARNING' ? 'bg-amber-500' : 'bg-rose-500'
              }`} />
              {status}
            </span>
          </div>
          <h3 className="text-lg font-bold text-slate-900 leading-snug">{plant.name}</h3>
          <p className="text-xs text-slate-500">{plant.code} • {plant.state_name || 'Grid Asset'}</p>
        </div>

        <button
          onClick={onClose}
          className="p-1 rounded-lg text-slate-400 hover:text-slate-700 hover:bg-slate-100 transition-colors"
        >
          <X className="w-5 h-5" />
        </button>
      </div>

      {/* Primary KPI Grid */}
      <div className="grid grid-cols-2 gap-3 my-4">
        <div className="bg-slate-50 p-3 rounded-xl border border-slate-200/80">
          <span className="text-[11px] font-semibold text-slate-500 block">Rated Capacity</span>
          <span className="text-xl font-extrabold text-slate-900">
            {Number(plant.capacity_mw).toLocaleString()} <span className="text-xs font-semibold text-slate-500">MW</span>
          </span>
        </div>
        <div className="bg-emerald-50/70 p-3 rounded-xl border border-emerald-200/70">
          <span className="text-[11px] font-semibold text-emerald-700 block">Live Generation</span>
          <span className="text-xl font-extrabold text-emerald-900">
            {Number(genMW).toFixed(1)} <span className="text-xs font-semibold text-emerald-700">MW</span>
          </span>
        </div>
        <div className="bg-blue-50/70 p-3 rounded-xl border border-blue-200/70">
          <span className="text-[11px] font-semibold text-blue-700 block">Capacity Factor (CUF)</span>
          <span className="text-xl font-extrabold text-blue-900">
            {cuf}%
          </span>
        </div>
        <div className="bg-purple-50/70 p-3 rounded-xl border border-purple-200/70">
          <span className="text-[11px] font-semibold text-purple-700 block">BESS Storage SoC</span>
          <span className="text-xl font-extrabold text-purple-900">
            {telemetry?.bess_soc_pct != null ? `${telemetry.bess_soc_pct}%` : 'Co-located'}
          </span>
        </div>
      </div>

      {/* Live Atmospheric Sensor Readings */}
      <div className="bg-slate-50/90 rounded-xl p-3.5 border border-slate-200/80 mb-4 text-xs">
        <span className="font-bold text-slate-800 block mb-2 flex items-center gap-1.5">
          <Activity className="w-3.5 h-3.5 text-emerald-600" />
          Atmospheric Telemetry
        </span>
        <div className="grid grid-cols-3 gap-2 text-slate-600">
          <div className="bg-white p-2 rounded-lg border border-slate-200/60">
            <span className="text-[10px] text-slate-400 block">Irradiance</span>
            <span className="font-bold text-slate-800">
              {telemetry?.weather?.irradiance_ghi ? `${Math.round(telemetry.weather.irradiance_ghi)} W/m²` : '850 W/m²'}
            </span>
          </div>
          <div className="bg-white p-2 rounded-lg border border-slate-200/60">
            <span className="text-[10px] text-slate-400 block">Wind 100m</span>
            <span className="font-bold text-slate-800">
              {telemetry?.weather?.wind_speed_ms ? `${Number(telemetry.weather.wind_speed_ms).toFixed(1)} m/s` : '6.4 m/s'}
            </span>
          </div>
          <div className="bg-white p-2 rounded-lg border border-slate-200/60">
            <span className="text-[10px] text-slate-400 block">Ambient Temp</span>
            <span className="font-bold text-slate-800">
              {telemetry?.weather?.ambient_temp_c ? `${Math.round(telemetry.weather.ambient_temp_c)}°C` : '32°C'}
            </span>
          </div>
        </div>
      </div>

      {/* 24-Hour Forecast Preview Chart */}
      <div className="bg-white rounded-xl p-3.5 border border-slate-200 mb-4">
        <div className="flex items-center justify-between mb-2">
          <span className="text-xs font-bold text-slate-900 flex items-center gap-1.5">
            <TrendingUp className="w-3.5 h-3.5 text-emerald-600" />
            24h Day-Ahead Forecast Curve
          </span>
          <span className="text-[10px] text-slate-400">Hourly (MW)</span>
        </div>
        <div className="h-28 w-full">
          <ResponsiveContainer width="100%" height="100%">
            <AreaChart data={chartPoints} margin={{ top: 5, right: 5, left: -25, bottom: 0 }}>
              <defs>
                <linearGradient id="curveColor" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="5%" stopColor="#10b981" stopOpacity={0.8}/>
                  <stop offset="95%" stopColor="#10b981" stopOpacity={0.05}/>
                </linearGradient>
              </defs>
              <XAxis dataKey="hour" tick={{ fontSize: 9 }} interval={5} stroke="#94a3b8" />
              <YAxis tick={{ fontSize: 9 }} stroke="#94a3b8" />
              <Tooltip 
                formatter={(val) => [`${val} MW`, 'Predicted']}
                labelFormatter={(label) => `Time: ${label}`}
                contentStyle={{ backgroundColor: '#0f172a', borderColor: '#334155', borderRadius: '8px', color: '#fff', fontSize: '11px' }}
              />
              <Area type="monotone" dataKey="predicted_mw" stroke="#059669" strokeWidth={2} fillOpacity={1} fill="url(#curveColor)" />
            </AreaChart>
          </ResponsiveContainer>
        </div>
      </div>

      {/* Active Operational Risk / Alert Notification */}
      {isAlert && (
        <div className="p-3 bg-rose-50 border border-rose-200 rounded-xl mb-4 text-xs">
          <div className="flex items-center gap-2 text-rose-800 font-bold mb-1">
            <ShieldAlert className="w-4 h-4 text-rose-600" />
            <span>Operational Risk Advisory</span>
          </div>
          <p className="text-slate-700 leading-relaxed text-[11px] mb-2">
            Rapid ramp event or atmospheric occlusions detected. Recommended action: Synchronize BESS dispatch to buffer grid interconnection bus.
          </p>
          <div className="p-2 bg-white rounded-lg border border-rose-200/80 text-[10px] text-rose-900 font-semibold">
            Action: BESS Charge Buffer / Spinning Reserve standby
          </div>
        </div>
      )}

      {/* Geolocation Coordinates Info */}
      <div className="mt-auto pt-3 border-t border-slate-200 text-[11px] text-slate-500 space-y-1">
        <div className="flex justify-between">
          <span>Coordinates:</span>
          <span className="font-mono text-slate-700">{plant.latitude?.toFixed(4)}°N, {plant.longitude?.toFixed(4)}°E</span>
        </div>
        <div className="flex justify-between">
          <span>Grid Interconnection:</span>
          <span className="font-semibold text-slate-700">{plant.region_name || 'Western/Northern Corridor'}</span>
        </div>
      </div>

    </div>
  );
}
