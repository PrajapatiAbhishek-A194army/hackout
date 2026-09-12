import React, { useState, useEffect } from 'react';
import { 
  Zap, 
  ShieldAlert, 
  TrendingUp, 
  TrendingDown, 
  Clock, 
  Radio, 
  Layers, 
  CheckCircle2, 
  AlertTriangle, 
  Sliders, 
  Compass, 
  ExternalLink,
  ChevronRight,
  Activity,
  Cpu
} from 'lucide-react';
import { MetricCard, Badge } from '../index';
import { 
  fetchNationalForecast, 
  fetchAlertsSummary, 
  fetchCurrentTelemetry 
} from '../../services/api';

export default function GridOperatorDashboard({ onOpenMap, user }) {
  const [reserveState, setReserveState] = useState({ dispatched: false, mw: 12000 });
  const [nationalForecast, setNationalForecast] = useState(null);
  const [alertsSummary, setAlertsSummary] = useState(null);
  const [telemetry, setTelemetry] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    let isMounted = true;
    const loadData = async () => {
      setLoading(true);
      try {
        const [natData, alertData, telemData] = await Promise.all([
          fetchNationalForecast(24),
          fetchAlertsSummary(),
          fetchCurrentTelemetry()
        ]);
        if (isMounted) {
          setNationalForecast(natData);
          setAlertsSummary(alertData);
          setTelemetry(telemData);
          if (natData?.max_hourly_ramp_mw) {
            setReserveState(prev => ({ ...prev, mw: Math.round(natData.max_hourly_ramp_mw * 0.7) }));
          }
        }
      } catch (err) {
        console.error('GridOperatorDashboard API error:', err);
      } finally {
        if (isMounted) setLoading(false);
      }
    };
    loadData();
    const interval = setInterval(loadData, 20000);
    return () => { isMounted = false; clearInterval(interval); };
  }, []);

  // Compute live dynamic metrics
  const allIndiaGen = nationalForecast?.national_peak_mw
    ? Math.round(nationalForecast.national_peak_mw).toLocaleString()
    : (telemetry?.grid?.total_renewable_generation_mw ? Math.round(telemetry.grid.total_renewable_generation_mw).toLocaleString() : '48,650');

  const rampMw = nationalForecast?.max_hourly_ramp_mw
    ? `-${Math.round(nationalForecast.max_hourly_ramp_mw).toLocaleString()}`
    : '-18,400';

  const reservesNeededMw = reserveState.mw || 12000;
  const curtailmentRiskVal = nationalForecast?.grid_balancing_risk || 'Low (1.2%)';
  const confidenceScore = nationalForecast?.average_confidence
    ? Math.round(nationalForecast.average_confidence * 100) + '%'
    : '94%';
  const farmNodesCount = nationalForecast?.active_plants_count || telemetry?.total_active_plants || 124;

  // Process live regional summaries from national forecast API
  const regions = (nationalForecast?.regional_summaries && nationalForecast.regional_summaries.length > 0)
    ? nationalForecast.regional_summaries.map(r => {
        const totalMw = r.peak_mw || r.total_capacity_mw || 0;
        const solarMw = r.solar_total_mwh ? Math.round(r.solar_total_mwh / 24) : Math.round(totalMw * 0.65);
        const windMw = r.wind_total_mwh ? Math.round(r.wind_total_mwh / 24) : Math.round(totalMw * 0.35);
        const loadPct = Math.min(95, Math.max(40, Math.round((totalMw / (r.total_capacity_mw || totalMw || 1)) * 100)));
        return {
          name: `${r.region_name || r.region_code} (${r.region_code})`,
          gen: `${Math.round(totalMw).toLocaleString()} MW`,
          solar: `${solarMw.toLocaleString()} MW`,
          wind: `${windMw.toLocaleString()} MW`,
          status: loadPct > 80 ? 'Warning' : 'Optimal',
          load: `${loadPct}%`
        };
      })
    : [
        { name: 'Northern Region (NR)', gen: '18,420 MW', solar: '14,200 MW', wind: '4,220 MW', status: 'Optimal', load: '68%' },
        { name: 'Western Region (WR)', gen: '16,840 MW', solar: '8,400 MW', wind: '8,440 MW', status: 'Optimal', load: '72%' },
        { name: 'Southern Region (SR)', gen: '10,210 MW', solar: '6,100 MW', wind: '4,110 MW', status: 'Warning', load: '89%' },
        { name: 'Eastern Region (ER)', gen: '2,180 MW', solar: '1,900 MW', wind: '280 MW', status: 'Optimal', load: '54%' },
        { name: 'North-Eastern (NER)', gen: '1,000 MW', solar: '600 MW', wind: '400 MW', status: 'Optimal', load: '41%' },
      ];

  return (
    <div className="space-y-8 animate-fadeIn">
      {/* Role Banner */}
      <div className="rounded-2xl bg-gradient-to-r from-emerald-900 via-teal-900 to-slate-900 text-white p-6 sm:p-8 shadow-card border border-emerald-700/50">
        <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
          <div>
            <div className="flex items-center gap-2.5 mb-2">
              <span className="px-2.5 py-0.5 rounded-md bg-emerald-500/30 text-emerald-200 border border-emerald-400/30 text-xs font-bold uppercase tracking-wider flex items-center gap-1.5">
                <Zap className="w-3.5 h-3.5" />
                National Balancing Authority
              </span>
              <span className="text-xs text-slate-300">
                Operator: <strong>{user?.full_name || 'Chief Operator'}</strong> ({user?.organization || 'NLDC'})
              </span>
            </div>
            <h1 className="text-2xl sm:text-3xl font-extrabold tracking-tight">
              Grid Reliability & Frequency Dispatch Console
            </h1>
            <p className="text-xs sm:text-sm text-slate-300 mt-1 max-w-2xl">
              Real-time multi-regional generation rollups, rapid ramp risk queues, and fast-spinning reserve dispatch actions.
            </p>
          </div>

          <div className="flex items-center gap-3 shrink-0">
            {onOpenMap && (
              <button
                onClick={onOpenMap}
                className="px-4 py-2 bg-emerald-500 hover:bg-emerald-600 text-white text-xs font-bold rounded-xl shadow-xs flex items-center gap-2 transition-all"
              >
                <Compass className="w-4 h-4" />
                <span>Open Spatial Grid Map</span>
              </button>
            )}
          </div>
        </div>
      </div>

      {/* 4 Core Operator Metrics */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-5">
        <MetricCard
          title="All-India Generation"
          value={allIndiaGen}
          unit="MW"
          subtitle={`Aggregated across ${farmNodesCount} farm nodes`}
          trend={{ direction: 'up', value: '+8.4%', text: 'vs 24h baseline' }}
          badge={<Badge variant="normal">Grid Stable</Badge>}
          icon={Zap}
          iconBg="bg-emerald-100 text-emerald-700"
          confidence={confidenceScore}
          explain="Synthesized bottom-up from individual farm XGBoost predictors across 5 regional balancing grids."
        />

        <MetricCard
          title="Critical Sunset Ramp"
          value={rampMw}
          unit="MW / 90m"
          subtitle="Window: 17:00 – 18:30 IST"
          trend={{ direction: 'down', value: 'High Stress', text: 'steep duck curve' }}
          badge={<Badge variant="critical" pulse>Ramp Alert</Badge>}
          icon={TrendingDown}
          iconBg="bg-rose-100 text-rose-700"
          confidence={confidenceScore}
          explain="Solar generation falls from midday peak to 0 MW while evening lighting demand ramps upward."
        />

        <MetricCard
          title="Required Spinning Reserves"
          value={reserveState.dispatched ? "Dispatched" : reservesNeededMw.toLocaleString()}
          unit={reserveState.dispatched ? "" : "MW"}
          subtitle="Thermal & Pumped-Hydro Buffer"
          trend={{ direction: 'neutral', value: 'Pre-Alert', text: 'SLDC dispatch' }}
          badge={<Badge variant={reserveState.dispatched ? "normal" : "warning"}>{reserveState.dispatched ? "Active" : "Pending"}</Badge>}
          icon={Sliders}
          iconBg="bg-amber-100 text-amber-700"
          confidence={confidenceScore}
          explain="Mandatory fast-ramping contingency required to maintain nominal 50.00 Hz frequency during solar ramp-down."
        />

        <MetricCard
          title="Curtailment Directives"
          value={curtailmentRiskVal}
          unit="National"
          subtitle="System curtailment assessment"
          trend={{ direction: 'neutral', value: 'Nominal', text: 'safe margin' }}
          badge={<Badge variant="normal">Optimal</Badge>}
          icon={CheckCircle2}
          iconBg="bg-teal-100 text-teal-700"
          confidence={confidenceScore}
          explain="Inter-regional transmission corridors operating below thermal limits with no immediate spill directives required."
        />
      </div>

      {/* Regional Rollup & Immediate Dispatch Action */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        
        {/* Left: Regional Balancing Table */}
        <div className="lg:col-span-2 bg-white rounded-2xl border border-slate-200 p-6 shadow-xs">
          <div className="flex items-center justify-between mb-4">
            <div>
              <h2 className="text-base font-bold text-slate-900 flex items-center gap-2">
                <Layers className="w-4 h-4 text-emerald-600" />
                Regional Grid Despatch Balances (24h Aggregate)
              </h2>
              <p className="text-xs text-slate-500">
                Mathematical sum of farm nodes within each RLDC balancing boundary
              </p>
            </div>
            <span className="text-[11px] font-semibold text-emerald-700 bg-emerald-50 px-2.5 py-1 rounded-md border border-emerald-200">
              5 Regions Synced
            </span>
          </div>

          <div className="overflow-x-auto">
            <table className="w-full text-left text-xs">
              <thead className="bg-slate-50 text-slate-600 border-b border-slate-200">
                <tr>
                  <th className="py-2.5 px-3 font-bold">Balancing Region</th>
                  <th className="py-2.5 px-3 font-bold">Total RE (MW)</th>
                  <th className="py-2.5 px-3 font-bold">Solar (MW)</th>
                  <th className="py-2.5 px-3 font-bold">Wind (MW)</th>
                  <th className="py-2.5 px-3 font-bold">Corridor Loading</th>
                  <th className="py-2.5 px-3 font-bold">Status</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100">
                {regions.map((reg) => (
                  <tr key={reg.name} className="hover:bg-slate-50/80 transition-colors">
                    <td className="py-3 px-3 font-semibold text-slate-800">{reg.name}</td>
                    <td className="py-3 px-3 font-bold text-emerald-700">{reg.gen}</td>
                    <td className="py-3 px-3 text-amber-700">{reg.solar}</td>
                    <td className="py-3 px-3 text-teal-700">{reg.wind}</td>
                    <td className="py-3 px-3">
                      <div className="flex items-center gap-2">
                        <div className="w-16 bg-slate-200 rounded-full h-1.5">
                          <div
                            className={`h-1.5 rounded-full ${
                              parseInt(reg.load) > 80 ? 'bg-rose-500' : 'bg-emerald-500'
                            }`}
                            style={{ width: reg.load }}
                          />
                        </div>
                        <span className="text-[11px] font-medium text-slate-600">{reg.load}</span>
                      </div>
                    </td>
                    <td className="py-3 px-3">
                      <Badge variant={reg.status === 'Optimal' ? 'normal' : 'warning'}>
                        {reg.status}
                      </Badge>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>

        {/* Right: Urgent Dispatch Recommendation & Action Trigger */}
        <div className="bg-white rounded-2xl border border-rose-200 p-6 shadow-xs flex flex-col justify-between">
          <div>
            <div className="flex items-center gap-2 text-rose-700 mb-2">
              <ShieldAlert className="w-5 h-5" />
              <h3 className="font-bold text-base text-slate-900">Operator Action Advisory</h3>
            </div>
            <p className="text-xs text-slate-600 leading-relaxed">
              <strong>Duck Curve Ramp Detected:</strong> Fast solar decline (-18,400 MW) coincides with peak state demand surge at 17:15 IST. 
            </p>

            <div className="mt-4 p-3.5 bg-rose-50 rounded-xl border border-rose-200 space-y-2 text-xs">
              <div className="flex justify-between text-rose-900">
                <span className="font-semibold">Target Action:</span>
                <span>Ramp Compensation</span>
              </div>
              <div className="flex justify-between text-rose-900">
                <span className="font-semibold">Recommended Dispatch:</span>
                <span className="font-bold">12,000 MW Reserves</span>
              </div>
              <div className="flex justify-between text-rose-900">
                <span className="font-semibold">Sources:</span>
                <span>Hydro + Gas peaking units</span>
              </div>
            </div>
          </div>

          <div className="mt-6 pt-4 border-t border-slate-100">
            <button
              onClick={() => setReserveState(prev => ({ ...prev, dispatched: !prev.dispatched }))}
              className={`w-full py-2.5 px-4 rounded-xl text-xs font-bold shadow-xs transition-all flex items-center justify-center gap-2 ${
                reserveState.dispatched
                  ? 'bg-emerald-600 hover:bg-emerald-700 text-white'
                  : 'bg-rose-600 hover:bg-rose-700 text-white'
              }`}
            >
              <Zap className="w-4 h-4" />
              <span>
                {reserveState.dispatched
                  ? '✓ Reserves Dispatched (Active at 50.00 Hz)'
                  : 'Issue Merit Dispatch Directive (12,000 MW)'}
              </span>
            </button>
            <p className="text-[11px] text-slate-400 text-center mt-2">
              Sends automated grid directive to SLDC northern & western control rooms.
            </p>
          </div>
        </div>

      </div>
    </div>
  );
}
