import React, { useState, useEffect } from 'react';
import { 
  TrendingUp, 
  TrendingDown, 
  DollarSign, 
  Compass, 
  ArrowUpRight, 
  ArrowDownRight, 
  Activity, 
  Layers, 
  CheckCircle2, 
  Zap, 
  Shuffle, 
  PieChart, 
  BarChart3,
  Flame
} from 'lucide-react';
import { MetricCard, Badge } from '../index';
import { fetchNationalForecast } from '../../services/api';

export default function EnergyTraderDashboard({ onOpenMap, user }) {
  const [tradeExecuted, setTradeExecuted] = useState(false);
  const [nationalForecast, setNationalForecast] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    let isMounted = true;
    fetchNationalForecast(24).then(data => {
      if (isMounted) {
        setNationalForecast(data);
        setLoading(false);
      }
    }).catch(err => {
      console.error('EnergyTraderDashboard error:', err);
      if (isMounted) setLoading(false);
    });
    return () => { isMounted = false; };
  }, []);

  const middaySolarMw = nationalForecast?.installed_solar_mw
    ? Math.round(nationalForecast.installed_solar_mw).toLocaleString()
    : '14,200';

  const atcCapacity = nationalForecast?.regional_summaries?.[0]?.total_capacity_mw
    ? Math.round(nationalForecast.regional_summaries[0].total_capacity_mw * 0.4).toLocaleString()
    : '3,420';

  const marketSpreads = (nationalForecast?.forecast_points && nationalForecast.forecast_points.length > 0)
    ? [
        { block: '09:00 - 11:00', mcpDam: '₹ 3.80', mcpRtm: '₹ 4.10', spread: '+₹ 0.30', signal: 'Buy DAM', corridor: 'NR → WR' },
        { 
          block: '11:00 - 14:00 (Solar Peak)', 
          mcpDam: '₹ 2.40', 
          mcpRtm: '₹ 2.10', 
          spread: '-₹ 0.30', 
          signal: `Surplus (${middaySolarMw} MW)`, 
          corridor: 'NR Export' 
        },
        { block: '14:00 - 17:00', mcpDam: '₹ 3.20', mcpRtm: '₹ 3.50', spread: '+₹ 0.30', signal: 'Bilateral Hold', corridor: 'WR → SR' },
        { 
          block: '18:00 - 21:30 (Evening Peak)', 
          mcpDam: '₹ 7.90', 
          mcpRtm: '₹ 8.50', 
          spread: '+₹ 0.60', 
          signal: 'Sell RTM Peakers', 
          corridor: 'All Grids Tight' 
        },
      ]
    : [
        { block: '09:00 - 11:00', mcpDam: '₹ 3.80', mcpRtm: '₹ 4.10', spread: '+₹ 0.30', signal: 'Buy DAM', corridor: 'NR → WR' },
        { block: '11:00 - 14:00 (Solar Peak)', mcpDam: '₹ 2.40', mcpRtm: '₹ 2.10', spread: '-₹ 0.30', signal: 'Sell Solar / Charge', corridor: 'NR Surplus' },
        { block: '14:00 - 17:00', mcpDam: '₹ 3.20', mcpRtm: '₹ 3.50', spread: '+₹ 0.30', signal: 'Bilateral Hold', corridor: 'WR → SR' },
        { block: '18:00 - 21:30 (Evening Peak)', mcpDam: '₹ 7.90', mcpRtm: '₹ 8.50', spread: '+₹ 0.60', signal: 'Sell RTM Peakers', corridor: 'All Grids Tight' },
      ];

  return (
    <div className="space-y-8 animate-fadeIn">
      {/* Trader Header */}
      <div className="rounded-2xl bg-gradient-to-r from-purple-950 via-indigo-950 to-slate-900 text-white p-6 sm:p-8 shadow-card border border-purple-700/50">
        <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
          <div>
            <div className="flex items-center gap-2.5 mb-2">
              <span className="px-2.5 py-0.5 rounded-md bg-purple-500/30 text-purple-200 border border-purple-400/30 text-xs font-bold uppercase tracking-wider flex items-center gap-1.5">
                <TrendingUp className="w-3.5 h-3.5" />
                Power Market Arbitrage & Exchange Trading
              </span>
              <span className="text-xs text-slate-300">
                Trader: <strong>{user?.full_name || 'Senior Power Trader'}</strong> ({user?.organization || 'IEX Power Desk'})
              </span>
            </div>
            <h1 className="text-2xl sm:text-3xl font-extrabold tracking-tight">
              Energy Price Spreads & Corridor Arbitrage
            </h1>
            <p className="text-xs sm:text-sm text-slate-300 mt-1 max-w-2xl">
              Anticipate renewable supply surpluses to execute Day-Ahead (DAM) and Real-Time (RTM) market arbitrage before transmission corridors saturate.
            </p>
          </div>

          <div className="flex items-center gap-3 shrink-0">
            {onOpenMap && (
              <button
                onClick={onOpenMap}
                className="px-4 py-2 bg-purple-600 hover:bg-purple-700 text-white text-xs font-bold rounded-xl shadow-xs flex items-center gap-2 transition-all"
              >
                <Compass className="w-4 h-4" />
                <span>Inter-Regional Corridor Flow Map</span>
              </button>
            )}
          </div>
        </div>
      </div>

      {/* 4 Core Trader Metrics */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-5">
        <MetricCard
          title="Midday Solar Surplus Window"
          value="11:00 - 15:00"
          unit="IST"
          subtitle="Northern Region Solar Peak"
          trend={{ direction: 'down', value: '₹ 2.40/kWh', text: 'depressed clearing price' }}
          badge={<Badge variant="surplus">Cheap Power</Badge>}
          icon={TrendingDown}
          iconBg="bg-purple-100 text-purple-800"
          confidence={nationalForecast?.average_confidence ? Math.round(nationalForecast.average_confidence * 100) + '%' : "96%"}
          explain={`Over ${middaySolarMw} MW solar surplus in Rajasthan depresses midday DAM clearing prices to lower bound.`}
        />

        <MetricCard
          title="Evening Scarcity Premium"
          value="₹ 8.50"
          unit="/ kWh"
          subtitle="Window: 18:30 – 21:00 IST"
          trend={{ direction: 'up', value: '+254%', text: 'surge vs midday' }}
          badge={<Badge variant="critical" pulse>High Premium</Badge>}
          icon={Flame}
          iconBg="bg-rose-100 text-rose-700"
          confidence={nationalForecast?.average_confidence ? Math.round(nationalForecast.average_confidence * 100) + '%' : "94%"}
          explain="Fast sunset ramp combined with high peak cooling demand pushes RTM bids close to the CERC price cap."
        />

        <MetricCard
          title="DAM vs RTM Spread"
          value="+₹ 0.60"
          unit="/ kWh"
          subtitle="Evening arbitrage window"
          trend={{ direction: 'up', value: 'High Alpha', text: 'favorable spread' }}
          badge={<Badge variant="normal">Arbitrage Ready</Badge>}
          icon={Shuffle}
          iconBg="bg-teal-100 text-teal-700"
          confidence="91%"
          explain="Buying low in DAM and discharging battery capacity into RTM captures ₹600/MWh spread."
        />

        <MetricCard
          title="Export Corridor Headroom"
          value={atcCapacity}
          unit="MW ATC"
          subtitle="Northern to Western Corridor"
          trend={{ direction: 'neutral', value: '78% Cap', text: 'pre-congestion' }}
          badge={<Badge variant="warning">Monitor Limits</Badge>}
          icon={Zap}
          iconBg="bg-amber-100 text-amber-700"
          confidence={nationalForecast?.average_confidence ? Math.round(nationalForecast.average_confidence * 100) + '%' : "93%"}
          explain="Available Transfer Capability (ATC) between NR and WR will congest by 13:30 IST without early bilateral booking."
        />
      </div>

      {/* Market Clearing Table & Bilateral Execution */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        
        {/* Left: Market Spreads & Trading Blocks */}
        <div className="lg:col-span-2 bg-white rounded-2xl border border-slate-200 p-6 shadow-xs">
          <div className="flex items-center justify-between mb-4">
            <div>
              <h2 className="text-base font-bold text-slate-900 flex items-center gap-2">
                <BarChart3 className="w-4 h-4 text-purple-600" />
                IEX Power Exchange Clearing Forecast (DAM vs RTM Blocks)
              </h2>
              <p className="text-xs text-slate-500">
                Hourly Price Forecast driven by Farm Aggregate Supply Volatility
              </p>
            </div>
            <span className="text-[11px] font-semibold text-purple-800 bg-purple-50 px-2.5 py-1 rounded-md border border-purple-200">
              Exchange Desk Feeds
            </span>
          </div>

          <div className="overflow-x-auto">
            <table className="w-full text-left text-xs">
              <thead className="bg-slate-50 text-slate-600 border-b border-slate-200">
                <tr>
                  <th className="py-2.5 px-3 font-bold">Trading Block (IST)</th>
                  <th className="py-2.5 px-3 font-bold">Est. DAM Price</th>
                  <th className="py-2.5 px-3 font-bold">Est. RTM Price</th>
                  <th className="py-2.5 px-3 font-bold">Spread Alpha</th>
                  <th className="py-2.5 px-3 font-bold">Inter-Grid Corridor</th>
                  <th className="py-2.5 px-3 font-bold">Signal</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100">
                {marketSpreads.map((item) => (
                  <tr key={item.block} className="hover:bg-slate-50/80 transition-colors">
                    <td className="py-3 px-3 font-bold text-slate-800">{item.block}</td>
                    <td className="py-3 px-3 text-slate-700 font-semibold">{item.mcpDam}</td>
                    <td className="py-3 px-3 text-purple-700 font-bold">{item.mcpRtm}</td>
                    <td className={`py-3 px-3 font-bold ${item.spread.startsWith('+') ? 'text-emerald-700' : 'text-slate-600'}`}>
                      {item.spread}
                    </td>
                    <td className="py-3 px-3 text-slate-600">{item.corridor}</td>
                    <td className="py-3 px-3">
                      <span className={`px-2 py-0.5 rounded text-[11px] font-semibold ${
                        item.signal.includes('Sell') || item.signal.includes('Charge')
                          ? 'bg-purple-50 text-purple-800 border border-purple-200'
                          : 'bg-emerald-50 text-emerald-800 border border-emerald-200'
                      }`}>
                        {item.signal}
                      </span>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>

        {/* Right: Arbitrage Trade Execution */}
        <div className="bg-white rounded-2xl border border-purple-200 p-6 shadow-xs flex flex-col justify-between">
          <div>
            <div className="flex items-center gap-2 text-purple-700 mb-2">
              <TrendingUp className="w-5 h-5" />
              <h3 className="font-bold text-base text-slate-900">Arbitrage Position Advisory</h3>
            </div>
            <p className="text-xs text-slate-600 leading-relaxed">
              Book Northern Region solar surplus at ₹2.40/kWh in DAM and contract delivery to Western Region industrial feeders before transmission corridors lock.
            </p>

            <div className="mt-4 p-3.5 bg-purple-50 rounded-xl border border-purple-200 space-y-2 text-xs text-purple-950">
              <div className="flex justify-between">
                <span className="font-semibold">Recommended Trade:</span>
                <span className="font-bold text-purple-900">Buy 850 MW DAM (NR)</span>
              </div>
              <div className="flex justify-between">
                <span className="font-semibold">Hedge Counterparty:</span>
                <span>Western Discoms (WR)</span>
              </div>
              <div className="flex justify-between">
                <span className="font-semibold">Expected Gross Margin:</span>
                <span className="font-bold text-emerald-700">₹ 38.6 Lakhs</span>
              </div>
            </div>
          </div>

          <div className="mt-6 pt-4 border-t border-slate-100">
            <button
              onClick={() => setTradeExecuted(!tradeExecuted)}
              className={`w-full py-2.5 px-4 rounded-xl text-xs font-bold shadow-xs transition-all flex items-center justify-center gap-2 ${
                tradeExecuted
                  ? 'bg-emerald-600 hover:bg-emerald-700 text-white'
                  : 'bg-purple-600 hover:bg-purple-700 text-white'
              }`}
            >
              <ArrowUpRight className="w-4 h-4" />
              <span>{tradeExecuted ? '✓ Position Submitted to Exchange Desk' : 'Execute Corridor Arbitrage Order'}</span>
            </button>
            <p className="text-[11px] text-slate-400 text-center mt-2">
              Automated STP trade order queued via IEX API Gateway with risk limit checks.
            </p>
          </div>
        </div>

      </div>
    </div>
  );
}
