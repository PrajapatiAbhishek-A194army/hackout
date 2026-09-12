import React, { useState, useEffect } from 'react';
import { 
  SunMedium, 
  Wind, 
  Activity, 
  Wrench, 
  CloudSun, 
  Thermometer, 
  Droplets, 
  CheckCircle2, 
  Compass, 
  Sparkles, 
  SlidersHorizontal, 
  ChevronRight,
  Building 
} from 'lucide-react';
import { MetricCard, Badge } from '../index';
import { fetchPlants, fetchFarmForecast, fetchPlantWeather } from '../../services/api';

export default function PlantOwnerDashboard({ onOpenMap, user }) {
  const [cleaningQueued, setCleaningQueued] = useState(false);
  const [plants, setPlants] = useState([]);
  const [selectedPlantId, setSelectedPlantId] = useState(null);
  const [farmForecast, setFarmForecast] = useState(null);
  const [weatherData, setWeatherData] = useState([]);
  const [loading, setLoading] = useState(true);

  // Load plants from database
  useEffect(() => {
    let isMounted = true;
    fetchPlants().then(data => {
      if (isMounted && data && data.length > 0) {
        setPlants(data);
        setSelectedPlantId(data[0].id);
      }
    });
    return () => { isMounted = false; };
  }, []);

  // When selected plant changes, fetch its live ML forecast and weather readings
  useEffect(() => {
    if (!selectedPlantId) return;
    let isMounted = true;
    setLoading(true);

    Promise.all([
      fetchFarmForecast(selectedPlantId, 24),
      fetchPlantWeather(selectedPlantId, 12)
    ]).then(([fc, weather]) => {
      if (isMounted) {
        setFarmForecast(fc);
        setWeatherData(weather || []);
        setLoading(false);
      }
    }).catch(err => {
      console.error('Failed to load plant telemetry:', err);
      if (isMounted) setLoading(false);
    });

    return () => { isMounted = false; };
  }, [selectedPlantId]);

  const currentPlant = plants.find(p => p.id === selectedPlantId) || plants[0] || {
    id: 1,
    name: 'Bhadla Solar Park Sec-IV',
    code: 'BHADLA_04',
    plant_type: 'solar',
    capacity_mw: 300
  };

  const peakMw = farmForecast?.peak_generation_mw 
    ? Math.round(farmForecast.peak_generation_mw).toLocaleString() 
    : Math.round((currentPlant.capacity_mw || 300) * 0.94).toLocaleString();

  const cufPct = farmForecast?.capacity_factor_pct 
    ? `${farmForecast.capacity_factor_pct}%` 
    : '27.4%';

  const latestW = weatherData[0] || {};

  const weatherDrivers = [
    { 
      label: 'Global Horizontal Irradiance (GHI)', 
      value: latestW.ghi !== undefined ? `${Math.round(latestW.ghi)} W/m²` : '948 W/m²', 
      impact: '+84 MW Peak Irradiance', 
      icon: SunMedium, 
      color: 'text-amber-600' 
    },
    { 
      label: 'Hub-Height Wind Speed (100m)', 
      value: latestW.wind_speed_100m !== undefined ? `${latestW.wind_speed_100m} m/s` : '7.8 m/s', 
      impact: '+32 MW Turbine Yield', 
      icon: Wind, 
      color: 'text-teal-600' 
    },
    { 
      label: 'Ambient Temperature', 
      value: latestW.temperature_c !== undefined ? `${latestW.temperature_c} °C` : '38.4 °C', 
      impact: '-4.2% Inverter Derating', 
      icon: Thermometer, 
      color: 'text-rose-600' 
    },
    { 
      label: 'Cloud Optical Cover', 
      value: latestW.cloud_cover_pct !== undefined ? `${Math.round(latestW.cloud_cover_pct)}% Cover` : '8.2% Cover', 
      impact: 'Clear Sky Optimal', 
      icon: CloudSun, 
      color: 'text-blue-600' 
    },
  ];

  return (
    <div className="space-y-8 animate-fadeIn">
      {/* Plant Owner Banner */}
      <div className="rounded-2xl bg-gradient-to-r from-blue-900 via-sky-950 to-slate-900 text-white p-6 sm:p-8 shadow-card border border-blue-700/50">
        <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
          <div>
            <div className="flex items-center gap-2.5 mb-2">
              <span className="px-2.5 py-0.5 rounded-md bg-blue-500/30 text-blue-200 border border-blue-400/30 text-xs font-bold uppercase tracking-wider flex items-center gap-1.5">
                <SunMedium className="w-3.5 h-3.5" />
                Renewable Asset Operations & IPP Console
              </span>
              <span className="text-xs text-slate-300">
                Asset Manager: <strong>{user?.full_name || 'Plant Operations Director'}</strong> ({user?.organization || 'Renewable IPP'})
              </span>
            </div>
            <h1 className="text-2xl sm:text-3xl font-extrabold tracking-tight">
              Farm Telemetry, CUF & Maintenance Optimizer
            </h1>
            <p className="text-xs sm:text-sm text-slate-300 mt-1 max-w-2xl">
              Inspect farm-level XGBoost predictions, evaluate weather drivers (GHI, wind vectors, heat derating), and schedule downtime with zero generation loss.
            </p>
          </div>

          <div className="flex items-center gap-3 shrink-0">
            {plants.length > 0 && (
              <div className="flex items-center gap-2 bg-white/10 px-3 py-1.5 rounded-xl border border-white/20 text-xs">
                <Building className="w-4 h-4 text-blue-300" />
                <select
                  value={selectedPlantId || ''}
                  onChange={(e) => setSelectedPlantId(Number(e.target.value))}
                  className="bg-transparent text-white font-semibold focus:outline-hidden cursor-pointer"
                >
                  {plants.map(p => (
                    <option key={p.id} value={p.id} className="text-slate-900 bg-white">
                      {p.name} ({p.capacity_mw} MW)
                    </option>
                  ))}
                </select>
              </div>
            )}
            {onOpenMap && (
              <button
                onClick={onOpenMap}
                className="px-4 py-2 bg-blue-600 hover:bg-blue-700 text-white text-xs font-bold rounded-xl shadow-xs flex items-center gap-2 transition-all"
              >
                <Compass className="w-4 h-4" />
                <span>Farm Spatial Telemetry</span>
              </button>
            )}
          </div>
        </div>
      </div>

      {/* 4 Core Plant Owner Metrics */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-5">
        <MetricCard
          title="Predicted Generation Peak"
          value={peakMw}
          unit="MW"
          subtitle={`${currentPlant.name} (${currentPlant.capacity_mw} MW Cap)`}
          trend={{ direction: 'up', value: 'Live ML', text: 'forecast output' }}
          badge={<Badge variant="solar">{currentPlant.plant_type.toUpperCase()}</Badge>}
          icon={SunMedium}
          iconBg="bg-blue-100 text-blue-800"
          confidence={farmForecast?.average_confidence ? Math.round(farmForecast.average_confidence * 100) + '%' : "96%"}
          explain="Peak forecast calculated by site-specific XGBoost regressor incorporating live numerical weather."
        />

        <MetricCard
          title="Capacity Utilization (CUF)"
          value={cufPct}
          unit="24h"
          subtitle="Facility efficiency benchmark"
          trend={{ direction: 'up', value: '+4.9%', text: 'above regional baseline' }}
          badge={<Badge variant="normal">Top Quartile</Badge>}
          icon={Activity}
          iconBg="bg-emerald-100 text-emerald-700"
          confidence={farmForecast?.average_confidence ? Math.round(farmForecast.average_confidence * 100) + '%' : "95%"}
          explain="Single-axis tracker optimization tracking sun elevation curve maximizes morning and afternoon energy capture."
        />

        <MetricCard
          title="Optimal Maintenance Window"
          value="01:00 - 05:00"
          unit="IST"
          subtitle="Tomorrow early morning"
          trend={{ direction: 'neutral', value: '0.0 MW Loss', text: 'no solar generation' }}
          badge={<Badge variant="normal">Zero Penalty</Badge>}
          icon={Wrench}
          iconBg="bg-teal-100 text-teal-700"
          confidence="99%"
          explain="Scheduling string inverter inspection during night hours prevents deviation penalties and lost tariff revenue."
        />

        <MetricCard
          title="Soiling & Thermal Losses"
          value={cleaningQueued ? "-1.1%" : "-4.2%"}
          unit="Derating"
          subtitle="Inverter temperature derating"
          trend={{ direction: 'down', value: 'Dust Layer', text: 'cleaning recommended' }}
          badge={<Badge variant={cleaningQueued ? "normal" : "warning"}>
            {cleaningQueued ? "Robots Active" : "Wash Advisory"}
          </Badge>}
          icon={Droplets}
          iconBg="bg-amber-100 text-amber-700"
          confidence="92%"
          explain="Automated robotic dry-cleaning cycle recovers up to 9.2 MW in peak irradiance hours."
        />
      </div>

      {/* Asset Switcher & Meteorological Drivers */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        
        {/* Left: Weather Driver Analysis Table */}
        <div className="lg:col-span-2 bg-white rounded-2xl border border-slate-200 p-6 shadow-xs">
          <div className="flex items-center justify-between mb-4">
            <div>
              <h2 className="text-base font-bold text-slate-900 flex items-center gap-2">
                <SlidersHorizontal className="w-4 h-4 text-blue-600" />
                Farm-Level Weather Regressors & Generation Drivers
              </h2>
              <p className="text-xs text-slate-500">
                Primary meteorological variables driving the site-specific XGBoost model
              </p>
            </div>
            <span className="text-[11px] font-semibold text-blue-800 bg-blue-50 px-2.5 py-1 rounded-md border border-blue-200">
              Site Sensor Feed
            </span>
          </div>

          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
            {weatherDrivers.map((driver) => {
              const Icon = driver.icon;
              return (
                <div key={driver.label} className="p-4 rounded-xl border border-slate-200/80 bg-slate-50/50 hover:bg-white hover:border-blue-300 transition-all">
                  <div className="flex items-center gap-2.5 mb-2">
                    <div className="p-2 rounded-lg bg-white shadow-xs">
                      <Icon className={`w-4 h-4 ${driver.color}`} />
                    </div>
                    <div>
                      <div className="text-[11px] font-semibold text-slate-500">{driver.label}</div>
                      <div className="text-base font-bold text-slate-900">{driver.value}</div>
                    </div>
                  </div>
                  <div className="text-xs font-semibold text-emerald-700 bg-emerald-50/80 px-2.5 py-1 rounded-md inline-block">
                    Impact: {driver.impact}
                  </div>
                </div>
              );
            })}
          </div>

          <div className="mt-6 p-4 rounded-xl bg-blue-50/70 border border-blue-200 flex items-start gap-3 text-xs text-blue-950">
            <Sparkles className="w-5 h-5 text-blue-600 shrink-0 mt-0.5" />
            <div>
              <strong>Explainability Insight:</strong> High midday ambient temperature (38.4°C) causes silicon panel voltage drop. 
              The XGBoost model automatically factors in negative temperature coefficients (-0.38%/°C) to prevent over-forecasting.
            </div>
          </div>
        </div>

        {/* Right: Asset Health & Maintenance Action */}
        <div className="bg-white rounded-2xl border border-blue-200 p-6 shadow-xs flex flex-col justify-between">
          <div>
            <div className="flex items-center gap-2 text-blue-700 mb-2">
              <Wrench className="w-5 h-5" />
              <h3 className="font-bold text-base text-slate-900">Preventive Maintenance Schedule</h3>
            </div>
            <p className="text-xs text-slate-600 leading-relaxed">
              Plan scheduled inverter maintenance and robotic array cleaning during zero-generation night cycles.
            </p>

            <div className="mt-4 p-3.5 bg-blue-50 rounded-xl border border-blue-200 space-y-2.5 text-xs text-blue-950">
              <div className="flex justify-between">
                <span className="font-semibold">Selected Asset:</span>
                <span className="font-bold text-blue-900">Bhadla Solar Block IV</span>
              </div>
              <div className="flex justify-between">
                <span className="font-semibold">Optimal Window:</span>
                <span className="font-bold text-emerald-700">01:00 – 05:00 IST</span>
              </div>
              <div className="flex justify-between">
                <span className="font-semibold">Target Action:</span>
                <span>Inverter Station Inspec. #4</span>
              </div>
              <div className="flex justify-between">
                <span className="font-semibold">Revenue Protection:</span>
                <span className="font-bold text-emerald-700">₹ 8.4 Lakhs Preserved</span>
              </div>
            </div>
          </div>

          <div className="mt-6 pt-4 border-t border-slate-100">
            <button
              onClick={() => setCleaningQueued(!cleaningQueued)}
              className={`w-full py-2.5 px-4 rounded-xl text-xs font-bold shadow-xs transition-all flex items-center justify-center gap-2 ${
                cleaningQueued
                  ? 'bg-emerald-600 hover:bg-emerald-700 text-white'
                  : 'bg-blue-600 hover:bg-blue-700 text-white'
              }`}
            >
              <Wrench className="w-4 h-4" />
              <span>{cleaningQueued ? '✓ Night Maintenance Window Queued' : 'Schedule Night Maintenance (01:00 IST)'}</span>
            </button>
            <p className="text-[11px] text-slate-400 text-center mt-2">
              Logs scheduled outage with the State Load Despatch Centre to waive DSM penalties.
            </p>
          </div>
        </div>

      </div>
    </div>
  );
}
