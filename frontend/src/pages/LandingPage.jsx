import React, { useState } from 'react';
import { 
  Zap, 
  Sun, 
  Wind, 
  Layers, 
  ShieldAlert, 
  BatteryCharging, 
  ArrowRight, 
  CheckCircle2, 
  TrendingUp, 
  TrendingDown, 
  AlertTriangle, 
  Activity, 
  Cpu, 
  CloudRain, 
  Clock, 
  Sliders, 
  Compass, 
  BarChart3, 
  Database,
  Search,
  ChevronRight,
  ExternalLink,
  ShieldCheck,
  Building2,
  PieChart,
  Boxes
} from 'lucide-react';
import { 
  MetricCard, 
  Badge, 
  ForecastHorizonSelector 
} from '../components';

export default function LandingPage({ activeRole, onSelectRole, onOpenMap, backendHealth, onOpenAuthModal }) {
  const [horizon, setHorizon] = useState('24h');
  const [selectedRoleTab, setSelectedRoleTab] = useState(activeRole || 'grid-operator');

  // Multi-horizon reactive metric simulations
  const horizonMetrics = {
    '24h': {
      totalMW: '48,650',
      solarMW: '31,200',
      windMW: '17,450',
      solarPct: 64,
      windPct: 36,
      confidence: '94%',
      confStatus: 'High Reliability',
      activeAlerts: 3,
      criticalCount: 1,
      warningCount: 2,
      peakHour: '13:00 IST',
      curtailmentRisk: 'Low (1.2%)'
    },
    '48h': {
      totalMW: '94,180',
      solarMW: '59,800',
      windMW: '34,380',
      solarPct: 63,
      windPct: 37,
      confidence: '86%',
      confStatus: 'Moderate-High',
      activeAlerts: 7,
      criticalCount: 2,
      warningCount: 5,
      peakHour: 'Tomorrow 13:30 IST',
      curtailmentRisk: 'Medium (3.8%)'
    },
    '72h': {
      totalMW: '138,420',
      solarMW: '87,600',
      windMW: '50,820',
      solarPct: 63,
      windPct: 37,
      confidence: '78%',
      confStatus: 'Weather Variance',
      activeAlerts: 11,
      criticalCount: 4,
      warningCount: 7,
      peakHour: 'Day 3 12:45 IST',
      curtailmentRisk: 'Elevated (5.4%)'
    }
  };

  const metrics = horizonMetrics[horizon];

  // Operational Roles Definition
  const roleDetails = {
    'grid-operator': {
      title: 'National & State Grid Operator',
      subtitle: 'Balancing Authority & Transmission Reliability',
      question: 'Will variable renewable supply create a frequency or balancing risk in the next 24–72 hours?',
      topView: 'National aggregate forecast, state-level risk heat timeline, rapid ramp alerts, critical states queue.',
      keyActions: 'National → State → Region → Farm drill-down; dispatch spinning reserves; issue curtailment directives.',
      accent: 'border-emerald-500 bg-emerald-50/30',
      badgeColor: 'normal',
      kpis: [
        { label: 'National Generation', value: `${metrics.totalMW} MW`, note: 'Aggregate 24h output' },
        { label: 'Ramp Alert Window', value: '17:00 - 18:30 IST', note: 'Rapid evening solar drop (-18,400 MW)' },
        { label: 'Priority State', value: 'Rajasthan & Gujarat', note: 'High midday surplus expected' },
      ],
      recommendation: 'Pre-schedule 12,000 MW thermal backup & initiate pumped-hydro storage discharge starting 17:15 IST.'
    },
    'plant-owner': {
      title: 'Renewable Plant Owner & IPP',
      subtitle: 'Asset Performance & Revenue Optimization',
      question: 'How much power will my individual farm generate, what drives it, and when should I schedule maintenance?',
      topView: 'Farm-level hourly generation curve (MW), capacity utilization (CUF), weather drivers (GHI, wind speed, temp).',
      keyActions: 'Farm forecast inspection; identify low-generation maintenance windows; revenue calculation & deviation penalty avoidance.',
      accent: 'border-blue-500 bg-blue-50/30',
      badgeColor: 'info',
      kpis: [
        { label: 'Farm Predicted Peak', value: '284.6 MW', note: 'Bhadla Solar Park Section 2 (300 MW Cap)' },
        { label: 'Expected CUF', value: '26.8%', note: 'Clear sky radiation anticipated' },
        { label: 'Optimal Maint. Window', value: 'Tomorrow 01:00 - 05:00', note: 'Zero solar production period' },
      ],
      recommendation: 'Clean inverter arrays before 09:00 IST peak. Scheduled inverter inspection between 02:00-04:30 IST.'
    },
    'utility': {
      title: 'Discom & Utility Procurement Manager',
      subtitle: 'Power Balancing & Shortfall Avoidance',
      question: 'How much renewable power will be available versus expected consumer demand in our licensed service territory?',
      topView: 'Renewable supply vs. consumer demand curve, hourly surplus/shortfall comparison, procurement requirement flags.',
      keyActions: 'Day-ahead power exchange bidding; battery energy storage system (BESS) charging; avoid costly penalties.',
      accent: 'border-amber-500 bg-amber-50/30',
      badgeColor: 'warning',
      kpis: [
        { label: 'Renewable Supply Share', value: '41.2%', note: 'Of total state expected demand' },
        { label: 'Net Demand Peak', value: '19:30 IST', note: 'Duck curve peak post-solar generation' },
        { label: 'Procurement Gap', value: '3,850 MW', note: 'Between 18:00 - 22:00 IST' },
      ],
      recommendation: 'Procure 3,800 MW in the Day-Ahead Market (DAM) on IEX before 12:00 IST closure.'
    },
    'energy-trader': {
      title: 'Power Market Analyst & Energy Trader',
      subtitle: 'Regional Market Signals & Opportunity Detection',
      question: 'How will renewable supply shifts impact market clearing prices and regional transmission congestion?',
      topView: 'Regional renewable trend curves, surplus windows with depression risk, transmission corridor loading alerts.',
      keyActions: 'Regional supply trend analysis; evaluate real-time market (RTM) vs day-ahead market (DAM) spreads.',
      accent: 'border-purple-500 bg-purple-50/30',
      badgeColor: 'surplus',
      kpis: [
        { label: 'Surplus Opportunity', value: '11:00 - 15:00 IST', note: 'Northern Region solar abundance' },
        { label: 'Market Clearing Signal', value: 'Softening (₹2.40/kWh)', note: 'Depressed prices in afternoon DAM' },
        { label: 'Evening Price Signal', value: 'Tightening (₹8.50/kWh)', note: 'High premium on fast-ramping capacity' },
      ],
      recommendation: 'Position bilateral delivery contracts in Northern Grid for afternoon delivery; hedge evening ramp.'
    }
  };

  const currentRole = roleDetails[selectedRoleTab] || roleDetails['grid-operator'];

  return (
    <div className="space-y-12 py-6">
      
      {/* 1. HERO SECTION */}
      <section className="relative overflow-hidden rounded-3xl bg-gradient-to-br from-[#0a3622] via-[#0f5132] to-[#0d6832] text-white shadow-elevated border border-emerald-800/60 p-6 sm:p-10 lg:p-12">
        {/* Subtle grid background pattern */}
        <div className="absolute inset-0 bg-[linear-gradient(to_right,#ffffff0a_1px,transparent_1px),linear-gradient(to_bottom,#ffffff0a_1px,transparent_1px)] bg-[size:24px_24px] pointer-events-none" />
        
        <div className="relative z-10 max-w-4xl">
          {/* Enterprise Status & Grid Intelligence Pills */}
          <div className="flex flex-wrap items-center gap-3 mb-5">
            <span className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full bg-emerald-500/20 border border-emerald-400/30 text-emerald-200 text-xs font-semibold backdrop-blur-xs">
              <ShieldCheck className="w-3.5 h-3.5 text-emerald-400" />
              National Clean Energy Grid Intelligence
            </span>
            <span className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full bg-white/10 border border-white/20 text-white text-xs font-medium backdrop-blur-xs">
              <span className="h-2 w-2 rounded-full bg-emerald-400 animate-pulse" />
              Live Telemetry & Decision Dispatch
            </span>
          </div>

          {/* Main Headline */}
          <h1 className="text-3xl sm:text-5xl lg:text-5xl font-extrabold tracking-tight leading-tight">
            From Weather Uncertainty to <span className="text-emerald-300">Actionable Grid Decisions</span>
          </h1>

          {/* Executive Summary / Value Proposition */}
          <p className="mt-4 text-emerald-100 text-base sm:text-lg leading-relaxed font-normal">
            We don’t stop at <em>“how much will be generated?”</em> We answer{' '}
            <strong className="text-white font-semibold underline decoration-emerald-400 underline-offset-4">
              “where will the risk occur, when will it occur, and what should the decision-maker consider next?”
            </strong>
          </p>

          {/* Horizon Selector in Hero */}
          <div className="mt-8 pt-6 border-t border-emerald-600/50 flex flex-wrap items-center justify-between gap-4">
            <div className="flex items-center gap-3">
              <span className="text-xs uppercase tracking-wider font-semibold text-emerald-200">
                Active Horizon:
              </span>
              <ForecastHorizonSelector 
                value={horizon} 
                onChange={(h) => setHorizon(h)} 
              />
              {onOpenMap && (
                <button
                  onClick={onOpenMap}
                  className="inline-flex items-center gap-1.5 px-3.5 py-2 rounded-xl bg-white/10 hover:bg-white/20 border border-white/20 text-white text-xs font-semibold backdrop-blur-xs transition-all shadow-xs"
                >
                  <Compass className="w-4 h-4 text-emerald-300" />
                  <span>Interactive Spatial Map</span>
                  <ArrowRight className="w-3.5 h-3.5 text-emerald-300" />
                </button>
              )}
            </div>

            <div className="flex items-center gap-2 text-xs text-emerald-200">
              <Activity className="w-4 h-4 text-emerald-400 animate-pulse" />
              <span>Forecast Engine: <strong>Solar & Wind XGBoost</strong></span>
            </div>
          </div>
        </div>
      </section>

      {/* 2. OPERATIONAL TELEMETRY BAR */}
      <section>
        <div className="flex items-center justify-between mb-4">
          <div>
            <h2 className="text-base font-bold text-slate-900 tracking-tight flex items-center gap-2">
              <BarChart3 className="w-4 h-4 text-emerald-600" />
              <span>National Renewable Telemetry ({horizon} Horizon)</span>
            </h2>
            <p className="text-xs text-slate-500">
              Aggregated from farm-level XGBoost predictions across regional and state nodes
            </p>
          </div>
          <div className="flex items-center gap-2">
            {onOpenMap && (
              <button
                onClick={onOpenMap}
                className="inline-flex items-center gap-1.5 px-3 py-1 bg-emerald-50 text-emerald-800 border border-emerald-200 rounded-lg text-xs font-semibold hover:bg-emerald-100 transition-colors"
              >
                <Compass className="w-3.5 h-3.5 text-emerald-600" />
                <span className="hidden sm:inline">Spatial Map</span>
              </button>
            )}
            <Badge variant="normal" dot>
              Live Synthesis
            </Badge>
          </div>
        </div>

        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-5">
          {/* Card 1: Total Renewable Forecast */}
          <MetricCard
            title="Total Generation"
            value={metrics.totalMW}
            unit="MW"
            subtitle={`Forecast window: ${horizon}`}
            trend={{ direction: 'up', value: '+8.4%', text: 'vs previous cycle' }}
            badge={<Badge variant="normal">Optimal</Badge>}
            icon={Zap}
            iconBg="bg-emerald-100 text-emerald-700"
            confidence={metrics.confidence}
            explain="Synthesized from 124 farm nodes across 5 regional balancing grids."
          />

          {/* Card 2: Solar Generation */}
          <MetricCard
            title="Solar Output"
            value={metrics.solarMW}
            unit="MW"
            subtitle={`${metrics.solarPct}% of total renewable mix`}
            trend={{ direction: 'up', value: '+12.1%', text: 'high solar irradiance' }}
            badge={<Badge variant="solar">Solar XGBoost</Badge>}
            icon={Sun}
            iconBg="bg-amber-100 text-amber-700"
            confidence="96%"
            explain="Driven by GHI, cloud cover < 15%, and temperature-adjusted inverter efficiency."
          />

          {/* Card 3: Wind Generation */}
          <MetricCard
            title="Wind Output"
            value={metrics.windMW}
            unit="MW"
            subtitle={`${metrics.windPct}% of total renewable mix`}
            trend={{ direction: 'down', value: '-3.2%', text: 'coastal wind easing' }}
            badge={<Badge variant="wind">Wind XGBoost</Badge>}
            icon={Wind}
            iconBg="bg-teal-100 text-teal-700"
            confidence="91%"
            explain="Turbine hub-height 100m wind vectors combined with atmospheric pressure context."
          />

          {/* Card 4: Active Balancing Alerts */}
          <MetricCard
            title="Active Grid Risks"
            value={metrics.activeAlerts}
            unit="Events"
            subtitle={`${metrics.criticalCount} Critical • ${metrics.warningCount} Warnings`}
            trend={{ direction: 'neutral', value: metrics.curtailmentRisk, text: 'curtailment risk' }}
            badge={<Badge variant={metrics.criticalCount > 0 ? 'critical' : 'warning'} dot pulse>Risk Queue</Badge>}
            icon={ShieldAlert}
            iconBg="bg-rose-100 text-rose-700"
            confidence={metrics.confidence}
            explain="Ramp warning triggered near sunset (17:00–18:30 IST). Storage dispatch recommended."
          />
        </div>
      </section>

      {/* 3. INTERACTIVE 4-TIER FORECAST HIERARCHY */}
      <section className="card-enterprise p-6 sm:p-8">
        <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 mb-8">
          <div>
            <div className="flex items-center gap-2 mb-1">
              <Layers className="w-5 h-5 text-emerald-600" />
              <h2 className="text-xl font-bold text-slate-900">
                Forecast Hierarchy & Upward Aggregation Architecture
              </h2>
            </div>
            <p className="text-xs sm:text-sm text-slate-500 max-w-2xl">
              Strictly adheres to the core architectural design: <strong>Train only farm-level models</strong>, 
              then mathematically sum upward. No multi-level black box ML.
            </p>
          </div>
          <div className="shrink-0">
            <span className="inline-flex items-center gap-1 px-3 py-1 bg-emerald-50 text-emerald-800 border border-emerald-200 rounded-lg text-xs font-semibold">
              <CheckCircle2 className="w-3.5 h-3.5 text-emerald-600" />
              Mathematical Consistency
            </span>
          </div>
        </div>

        {/* 4 Steps Flow Grid */}
        <div className="grid grid-cols-1 md:grid-cols-4 gap-4 relative">
          
          {/* Level 1: Farm */}
          <div className="p-5 rounded-2xl bg-white border-2 border-emerald-500/80 shadow-card relative group hover:border-emerald-600 transition-all">
            <div className="w-8 h-8 rounded-lg bg-emerald-100 text-emerald-800 font-bold text-sm flex items-center justify-center mb-3">
              1
            </div>
            <div className="flex items-center justify-between mb-1">
              <h3 className="font-bold text-slate-900 text-base">Farm Level</h3>
              <Badge variant="normal">ML Regressors</Badge>
            </div>
            <p className="text-xs text-slate-500 mb-3">
              Individual solar or wind farm output calculated directly by XGBoost.
            </p>
            <div className="space-y-1.5 text-[11px] text-slate-600 bg-slate-50 p-2.5 rounded-lg border border-slate-200/70">
              <div className="flex justify-between">
                <span>Model:</span>
                <span className="font-semibold text-slate-800">Separate Solar & Wind</span>
              </div>
              <div className="flex justify-between">
                <span>Inputs:</span>
                <span className="font-semibold text-slate-800">Weather + History + Metadata</span>
              </div>
              <div className="flex justify-between">
                <span>Target:</span>
                <span className="font-semibold text-emerald-700">Hourly MW per Farm</span>
              </div>
            </div>
          </div>

          {/* Level 2: Region */}
          <div className="p-5 rounded-2xl bg-white border border-slate-200 shadow-card hover:border-emerald-400 transition-all">
            <div className="w-8 h-8 rounded-lg bg-slate-100 text-slate-700 font-bold text-sm flex items-center justify-center mb-3">
              2
            </div>
            <div className="flex items-center justify-between mb-1">
              <h3 className="font-bold text-slate-900 text-base">Region Level</h3>
              <Badge variant="neutral">Sum(Farms)</Badge>
            </div>
            <p className="text-xs text-slate-500 mb-3">
              Sum of farm forecasts mapped within regional grid balancing clusters.
            </p>
            <div className="space-y-1.5 text-[11px] text-slate-600 bg-slate-50 p-2.5 rounded-lg border border-slate-200/70">
              <div className="flex justify-between">
                <span>Aggregation:</span>
                <span className="font-semibold text-slate-800">Direct Farm Summation</span>
              </div>
              <div className="flex justify-between">
                <span>Purpose:</span>
                <span className="font-semibold text-slate-800">Local Balancing & Feeder Ops</span>
              </div>
              <div className="flex justify-between">
                <span>Example:</span>
                <span className="font-semibold text-emerald-700">Western Region: 16,840 MW</span>
              </div>
            </div>
          </div>

          {/* Level 3: State */}
          <div className="p-5 rounded-2xl bg-white border border-slate-200 shadow-card hover:border-emerald-400 transition-all">
            <div className="w-8 h-8 rounded-lg bg-slate-100 text-slate-700 font-bold text-sm flex items-center justify-center mb-3">
              3
            </div>
            <div className="flex items-center justify-between mb-1">
              <h3 className="font-bold text-slate-900 text-base">State Level</h3>
              <Badge variant="neutral">Sum(Regions)</Badge>
            </div>
            <p className="text-xs text-slate-500 mb-3">
              State aggregate forecasts enabling SLDC planning and merit dispatch.
            </p>
            <div className="space-y-1.5 text-[11px] text-slate-600 bg-slate-50 p-2.5 rounded-lg border border-slate-200/70">
              <div className="flex justify-between">
                <span>Consumer:</span>
                <span className="font-semibold text-slate-800">SLDCs & State Discoms</span>
              </div>
              <div className="flex justify-between">
                <span>Value:</span>
                <span className="font-semibold text-slate-800">State Risk Prioritization</span>
              </div>
              <div className="flex justify-between">
                <span>Example:</span>
                <span className="font-semibold text-emerald-700">Rajasthan: 14,200 MW</span>
              </div>
            </div>
          </div>

          {/* Level 4: National */}
          <div className="p-5 rounded-2xl bg-white border border-slate-200 shadow-card hover:border-emerald-400 transition-all">
            <div className="w-8 h-8 rounded-lg bg-emerald-600 text-white font-bold text-sm flex items-center justify-center mb-3">
              4
            </div>
            <div className="flex items-center justify-between mb-1">
              <h3 className="font-bold text-slate-900 text-base">National Level</h3>
              <Badge variant="normal">Sum(States)</Badge>
            </div>
            <p className="text-xs text-slate-500 mb-3">
              Macro grid overview for national transmission & inter-state corridors.
            </p>
            <div className="space-y-1.5 text-[11px] text-slate-600 bg-slate-50 p-2.5 rounded-lg border border-slate-200/70">
              <div className="flex justify-between">
                <span>Consumer:</span>
                <span className="font-semibold text-slate-800">NLDC & National Operators</span>
              </div>
              <div className="flex justify-between">
                <span>Value:</span>
                <span className="font-semibold text-slate-800">Corridor Load & Security</span>
              </div>
              <div className="flex justify-between">
                <span>Example:</span>
                <span className="font-semibold text-emerald-700">All India: {metrics.totalMW} MW</span>
              </div>
            </div>
          </div>

        </div>

        {/* Explainability note */}
        <div className="mt-6 p-4 rounded-xl bg-emerald-50/70 border border-emerald-200 flex items-start gap-3 text-xs text-emerald-900">
          <ShieldCheck className="w-5 h-5 text-emerald-700 shrink-0 mt-0.5" />
          <div className="leading-relaxed">
            <strong>Architectural Integrity:</strong> Predicting at individual farm nodes preserves site-specific atmospheric physics 
            (local cloud albedo, elevation, turbine hub-height wind vectors). Mathematically summing upward ensures 100% aggregation consistency 
            with zero arithmetic mismatch across Farm → Region → State → National balancing views.
          </div>
        </div>
      </section>

      {/* 4. DECISION SUPPORT & EXPLAINABLE ALERT ENGINE */}
      <section className="card-enterprise p-6 sm:p-8">
        <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 mb-6">
          <div>
            <div className="flex items-center gap-2 mb-1">
              <AlertTriangle className="w-5 h-5 text-amber-600" />
              <h2 className="text-xl font-bold text-slate-900">
                Alert Engine & Explainable Recommendations
              </h2>
            </div>
            <p className="text-xs sm:text-sm text-slate-500">
              Every alert contains a clear mathematical trigger, meteorological explanation, and specific actionable recommendation.
            </p>
          </div>
          <Badge variant="warning" dot pulse>
            Decision Support Layer
          </Badge>
        </div>

        {/* Alerts Grid */}
        <div className="grid grid-cols-1 md:grid-cols-2 gap-5">
          
          {/* Alert 1: Over-generation */}
          <div className="p-5 rounded-xl border border-purple-200 bg-purple-50/30 flex flex-col justify-between">
            <div>
              <div className="flex items-center justify-between mb-2">
                <span className="text-xs font-bold uppercase tracking-wider text-purple-800 flex items-center gap-1.5">
                  <TrendingUp className="w-4 h-4 text-purple-600" />
                  Over-Generation / Surplus Risk
                </span>
                <Badge variant="surplus">Surplus: +4,200 MW</Badge>
              </div>
              <h4 className="text-sm font-bold text-slate-900 mb-1">
                Midday Renewable Generation Exceeds Regional Evacuation Limit
              </h4>
              <p className="text-xs text-slate-600 mb-3">
                <strong>Trigger:</strong> Western Region solar forecast exceeds regional transmission line capability between 12:00–14:00 IST.
              </p>
              <div className="p-3 bg-white rounded-lg border border-purple-200/80 text-xs text-slate-700">
                <span className="font-semibold text-purple-900 block mb-0.5">Explainable AI Attribution:</span>
                "Sky clarity index reaches 0.94 in Bhadla & Pavagada clusters causing generation to exceed local demand by 28%."
              </div>
            </div>

            <div className="mt-4 pt-3 border-t border-purple-200/60 flex items-center justify-between text-xs">
              <span className="font-bold text-purple-900 flex items-center gap-1">
                <BatteryCharging className="w-4 h-4 text-purple-700" />
                Action: Charge Battery Storage & Schedule Controlled Curtailment
              </span>
            </div>
          </div>

          {/* Alert 2: Under-generation */}
          <div className="p-5 rounded-xl border border-rose-200 bg-rose-50/30 flex flex-col justify-between">
            <div>
              <div className="flex items-center justify-between mb-2">
                <span className="text-xs font-bold uppercase tracking-wider text-rose-800 flex items-center gap-1.5">
                  <TrendingDown className="w-4 h-4 text-rose-600" />
                  Under-Generation / Shortfall Alert
                </span>
                <Badge variant="critical">Shortfall: -3,600 MW</Badge>
              </div>
              <h4 className="text-sm font-bold text-slate-900 mb-1">
                Sudden Cloud Cover Depresses Southern Grid Solar Output
              </h4>
              <p className="text-xs text-slate-600 mb-3">
                <strong>Trigger:</strong> Tamil Nadu & Karnataka solar plants forecast to drop 44% below day-ahead commitment between 10:00–13:00 IST.
              </p>
              <div className="p-3 bg-white rounded-lg border border-rose-200/80 text-xs text-slate-700">
                <span className="font-semibold text-rose-900 block mb-0.5">Explainable AI Attribution:</span>
                "Open-Meteo convective precipitation front causes cloud cover to spike from 12% to 78% within 90 minutes."
              </div>
            </div>

            <div className="mt-4 pt-3 border-t border-rose-200/60 flex items-center justify-between text-xs">
              <span className="font-bold text-rose-900 flex items-center gap-1">
                <Zap className="w-4 h-4 text-rose-700" />
                Action: Activate Fast-Ramping Gas/Hydro Backup & Procure Power
              </span>
            </div>
          </div>

          {/* Alert 3: Rapid Ramp Warning */}
          <div className="p-5 rounded-xl border border-amber-200 bg-amber-50/30 flex flex-col justify-between">
            <div>
              <div className="flex items-center justify-between mb-2">
                <span className="text-xs font-bold uppercase tracking-wider text-amber-800 flex items-center gap-1.5">
                  <Clock className="w-4 h-4 text-amber-600" />
                  Evening Ramp Warning (Duck Curve)
                </span>
                <Badge variant="warning">Ramp: -18,400 MW / hr</Badge>
              </div>
              <h4 className="text-sm font-bold text-slate-900 mb-1">
                Steep Solar Descent Coincides with Peak Evening Consumer Demand
              </h4>
              <p className="text-xs text-slate-600 mb-3">
                <strong>Trigger:</strong> National solar falls from 28,500 MW to 1,200 MW between 17:00 and 18:30 IST as daylight ends.
              </p>
              <div className="p-3 bg-white rounded-lg border border-amber-200/80 text-xs text-slate-700">
                <span className="font-semibold text-amber-900 block mb-0.5">Explainable AI Attribution:</span>
                "Solar zenith angle changes rapidly; solar output falls 38% between 17:00-18:00 because daylight ends."
              </div>
            </div>

            <div className="mt-4 pt-3 border-t border-amber-200/60 flex items-center justify-between text-xs">
              <span className="font-bold text-amber-900 flex items-center gap-1">
                <BatteryCharging className="w-4 h-4 text-amber-700" />
                Action: Prepare Storage Discharge (BESS) 30 min Before Drop
              </span>
            </div>
          </div>

          {/* Alert 4: Forecast-Change Alert */}
          <div className="p-5 rounded-xl border border-teal-200 bg-teal-50/30 flex flex-col justify-between">
            <div>
              <div className="flex items-center justify-between mb-2">
                <span className="text-xs font-bold uppercase tracking-wider text-teal-800 flex items-center gap-1.5">
                  <CloudRain className="w-4 h-4 text-teal-600" />
                  Atmospheric Wind Shift Alert
                </span>
                <Badge variant="wind">Variance: +18% Wind</Badge>
              </div>
              <h4 className="text-sm font-bold text-slate-900 mb-1">
                Coastal Low-Pressure System Increases Wind Yield
              </h4>
              <p className="text-xs text-slate-600 mb-3">
                <strong>Trigger:</strong> Gujarat & Maharashtra coastal wind forecast upgraded from 6.2 m/s to 10.4 m/s over next 18 hours.
              </p>
              <div className="p-3 bg-white rounded-lg border border-teal-200/80 text-xs text-slate-700">
                <span className="font-semibold text-teal-900 block mb-0.5">Explainable AI Attribution:</span>
                "Arabian Sea depression deepens pressure gradient; wind turbine capacity factors rise from 31% to 68%."
              </div>
            </div>

            <div className="mt-4 pt-3 border-t border-teal-200/60 flex items-center justify-between text-xs">
              <span className="font-bold text-teal-900 flex items-center gap-1">
                <Sliders className="w-4 h-4 text-teal-700" />
                Action: Recheck Balancing Plan & Back-down Thermal Base-load
              </span>
            </div>
          </div>

        </div>
      </section>

      {/* 5. ROLE-SPECIFIC CONSOLE PREVIEWS */}
      <section className="card-enterprise p-6 sm:p-8">
        <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 mb-6">
          <div>
            <div className="flex items-center gap-2 mb-1">
              <Boxes className="w-5 h-5 text-emerald-600" />
              <h2 className="text-xl font-bold text-slate-900">
                Tailored Consoles for All 4 Grid Stakeholders
              </h2>
            </div>
            <p className="text-xs sm:text-sm text-slate-500">
              Same underlying data and forecasting engine — tailored decision interfaces for each operational persona.
            </p>
          </div>
          
          {/* Interactive Role Tabs */}
          <div className="flex items-center bg-slate-100 p-1 rounded-xl border border-slate-200 text-xs font-semibold overflow-x-auto">
            {Object.keys(roleDetails).map((key) => {
              const role = roleDetails[key];
              const isSelected = selectedRoleTab === key;
              return (
                <button
                  key={key}
                  onClick={() => {
                    setSelectedRoleTab(key);
                    if (onSelectRole) onSelectRole(key);
                  }}
                  className={`px-3.5 py-1.5 rounded-lg whitespace-nowrap transition-all ${
                    isSelected
                      ? 'bg-white text-emerald-800 shadow-xs border border-slate-200 font-bold'
                      : 'text-slate-600 hover:text-slate-900'
                  }`}
                >
                  {role.title.split('&')[0]}
                </button>
              );
            })}
          </div>
        </div>

        {/* Selected Role Interactive Card */}
        <div className={`rounded-2xl border-2 p-6 sm:p-8 transition-all ${currentRole.accent}`}>
          <div className="flex flex-col lg:flex-row lg:items-center justify-between gap-4 mb-6 pb-6 border-b border-slate-200/80">
            <div>
              <div className="flex items-center gap-2 mb-1">
                <Badge variant={currentRole.badgeColor}>Active Role View</Badge>
                <h3 className="text-xl font-extrabold text-slate-900">{currentRole.title}</h3>
              </div>
              <p className="text-xs sm:text-sm font-medium text-slate-600">{currentRole.subtitle}</p>
            </div>
            <div className="bg-white/80 backdrop-blur-xs p-3 rounded-xl border border-slate-200 max-w-md text-xs">
              <span className="font-semibold text-slate-500 uppercase tracking-wider block text-[10px] mb-0.5">
                Primary Question Answered:
              </span>
              <p className="font-semibold text-slate-800 italic">"{currentRole.question}"</p>
            </div>
          </div>

          {/* Role KPIs */}
          <div className="grid grid-cols-1 sm:grid-cols-3 gap-4 mb-6">
            {currentRole.kpis.map((kpi, idx) => (
              <div key={idx} className="bg-white rounded-xl p-4 border border-slate-200 shadow-xs">
                <span className="text-xs text-slate-500 font-semibold uppercase tracking-wider block mb-1">
                  {kpi.label}
                </span>
                <span className="text-xl font-bold text-slate-900 block">{kpi.value}</span>
                <span className="text-[11px] text-slate-400 mt-0.5 block">{kpi.note}</span>
              </div>
            ))}
          </div>

          {/* Role Operational Flow & Action */}
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4 text-xs">
            <div className="bg-white/80 p-4 rounded-xl border border-slate-200">
              <span className="font-bold text-slate-900 block mb-1">Top-Of-Screen Operational View:</span>
              <p className="text-slate-600 leading-relaxed">{currentRole.topView}</p>
            </div>

            <div className="bg-white/80 p-4 rounded-xl border border-slate-200">
              <span className="font-bold text-slate-900 block mb-1">Key Actions & Drill-down:</span>
              <p className="text-slate-600 leading-relaxed">{currentRole.keyActions}</p>
            </div>
          </div>

          {/* Action Recommendation Banner & Login/Launch CTA */}
          <div className="mt-5 p-4 bg-white rounded-xl border border-emerald-300 text-xs flex flex-col sm:flex-row sm:items-center justify-between gap-3 shadow-xs">
            <div className="flex items-center gap-2">
              <CheckCircle2 className="w-4 h-4 text-emerald-600 shrink-0" />
              <span className="text-slate-700">
                <strong>Recommended Operational Protocol:</strong> {currentRole.recommendation}
              </span>
            </div>
            {onOpenAuthModal && (
              <button
                onClick={() => onOpenAuthModal('login', selectedRoleTab)}
                className="shrink-0 px-3.5 py-1.5 bg-emerald-600 hover:bg-emerald-700 text-white font-bold rounded-lg transition-all flex items-center gap-1.5 shadow-xs"
              >
                <span>Launch {currentRole.title.split('&')[0]} Workspace</span>
                <ChevronRight className="w-3.5 h-3.5" />
              </button>
            )}
          </div>
        </div>
      </section>

      {/* 6. DATA STRATEGY & CREDIBILITY */}
      <section className="bg-gradient-to-br from-slate-900 to-slate-800 text-white rounded-3xl p-6 sm:p-10 shadow-card">
        <div className="max-w-3xl mb-8">
          <div className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full bg-emerald-500/20 border border-emerald-400/30 text-emerald-300 text-xs font-semibold mb-3">
            <Database className="w-3.5 h-3.5" />
            <span>Enterprise Ingestion & Telemetry Architecture</span>
          </div>
          <h2 className="text-2xl sm:text-3xl font-bold tracking-tight">
            Multi-Source Ingestion & SCADA Integration
          </h2>
          <p className="mt-2 text-slate-300 text-sm leading-relaxed">
            Continuous automated telemetry linking high-resolution numerical weather models, national power registries, 
            and real-time SCADA sensor streams. The architecture provides resilient data feeds ensuring high-availability 
            generation forecasts for national and state grid balancing authorities.
          </p>
        </div>

        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
          <div className="p-4 rounded-xl bg-slate-800/80 border border-slate-700">
            <h4 className="font-bold text-white text-sm flex items-center gap-2 mb-1">
              <Sun className="w-4 h-4 text-amber-400" />
              Numerical Weather NWP
            </h4>
            <p className="text-xs text-slate-300 mb-2">High-Resolution Coordinate Feed</p>
            <span className="text-[11px] text-slate-400 block">
              Continuous assimilation of GHI, direct normal irradiance, temperature, and 100m turbine hub-height wind vectors.
            </span>
          </div>

          <div className="p-4 rounded-xl bg-slate-800/80 border border-slate-700">
            <h4 className="font-bold text-white text-sm flex items-center gap-2 mb-1">
              <Database className="w-4 h-4 text-blue-400" />
              Atmospheric Reanalysis
            </h4>
            <p className="text-xs text-slate-300 mb-2">Solar & Wind Climatology</p>
            <span className="text-[11px] text-slate-400 block">
              Multi-decade irradiance and meteorological time-series for seasonal baseline normalization and anomaly detection.
            </span>
          </div>

          <div className="p-4 rounded-xl bg-slate-800/80 border border-slate-700">
            <h4 className="font-bold text-white text-sm flex items-center gap-2 mb-1">
              <Building2 className="w-4 h-4 text-emerald-400" />
              National Asset Registry
            </h4>
            <p className="text-xs text-slate-300 mb-2">Grid Authority Metadata</p>
            <span className="text-[11px] text-slate-400 block">
              Verified plant nameplate capacities, inverter specifications, interconnection nodes, and SLDC regional mappings.
            </span>
          </div>

          <div className="p-4 rounded-xl bg-slate-800/80 border border-slate-700">
            <h4 className="font-bold text-white text-sm flex items-center gap-2 mb-1">
              <Activity className="w-4 h-4 text-purple-400" />
              SCADA & IoT Gateway
            </h4>
            <p className="text-xs text-slate-300 mb-2">Real-Time Inverter Telemetry</p>
            <span className="text-[11px] text-slate-400 block">
              Substation telemetry adapters supporting Modbus, OPC-UA, and IEC 60870-5-104 grid communication standards.
            </span>
          </div>
        </div>
      </section>

    </div>
  );
}
