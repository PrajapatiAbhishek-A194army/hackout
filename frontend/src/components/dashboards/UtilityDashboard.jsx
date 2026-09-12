import React, { useState } from 'react';
import { 
  Building2, 
  TrendingUp, 
  BatteryCharging, 
  Clock, 
  AlertTriangle, 
  CheckCircle2, 
  ArrowUpRight, 
  DollarSign, 
  Compass,
  PieChart,
  BarChart3,
  ShieldCheck
} from 'lucide-react';
import { MetricCard, Badge } from '../index';

export default function UtilityDashboard({ onOpenMap, user }) {
  const [bessScheduled, setBessScheduled] = useState(false);
  const [bidSubmitted, setBidSubmitted] = useState(false);

  const hourlyBalance = [
    { hour: '08:00', demand: 18500, reGen: 14200, netDemand: 4300, status: 'Balanced' },
    { hour: '11:00', demand: 21000, reGen: 26400, netDemand: -5400, status: 'Surplus (BESS Charge)' },
    { hour: '13:00', demand: 22400, reGen: 31200, netDemand: -8800, status: 'Surplus (BESS Charge)' },
    { hour: '16:00', demand: 23100, reGen: 18600, netDemand: 4500, status: 'Tightening' },
    { hour: '18:30', demand: 25800, reGen: 7200, netDemand: 18600, status: 'Deficit (Procure DAM)' },
    { hour: '20:00', demand: 26400, reGen: 4100, netDemand: 22300, status: 'Peak Deficit' },
  ];

  return (
    <div className="space-y-8 animate-fadeIn">
      {/* Utility Header */}
      <div className="rounded-2xl bg-gradient-to-r from-amber-900 via-stone-900 to-slate-900 text-white p-6 sm:p-8 shadow-card border border-amber-700/50">
        <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
          <div>
            <div className="flex items-center gap-2.5 mb-2">
              <span className="px-2.5 py-0.5 rounded-md bg-amber-500/30 text-amber-200 border border-amber-400/30 text-xs font-bold uppercase tracking-wider flex items-center gap-1.5">
                <Building2 className="w-3.5 h-3.5" />
                DISCOM Power Procurement Authority
              </span>
              <span className="text-xs text-slate-300">
                Procurement Officer: <strong>{user?.full_name || 'Chief Procurement Officer'}</strong> ({user?.organization || 'State DISCOM'})
              </span>
            </div>
            <h1 className="text-2xl sm:text-3xl font-extrabold tracking-tight">
              Utility Supply-Demand & Net Load Management
            </h1>
            <p className="text-xs sm:text-sm text-slate-300 mt-1 max-w-2xl">
              Forecast consumer demand versus renewable availability to minimize deviation penalties (DSM) and optimize Day-Ahead Market (DAM) bidding.
            </p>
          </div>

          <div className="flex items-center gap-3 shrink-0">
            {onOpenMap && (
              <button
                onClick={onOpenMap}
                className="px-4 py-2 bg-amber-600 hover:bg-amber-700 text-white text-xs font-bold rounded-xl shadow-xs flex items-center gap-2 transition-all"
              >
                <Compass className="w-4 h-4" />
                <span>Geographic Substation View</span>
              </button>
            )}
          </div>
        </div>
      </div>

      {/* 4 Core Utility Metrics */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-5">
        <MetricCard
          title="Renewable Supply Share"
          value="41.2%"
          unit="Mix"
          subtitle="Of total licensed territory load"
          trend={{ direction: 'up', value: '+4.5%', text: 'vs seasonal average' }}
          badge={<Badge variant="normal">High Green Mix</Badge>}
          icon={PieChart}
          iconBg="bg-amber-100 text-amber-800"
          confidence="95%"
          explain="Driven by high irradiance across state solar parks reducing daytime thermal power purchase cost."
        />

        <MetricCard
          title="Evening Procurement Gap"
          value={bidSubmitted ? "Covered" : "3,850"}
          unit={bidSubmitted ? "" : "MW"}
          subtitle="Shortfall window: 18:00 - 22:00 IST"
          trend={{ direction: 'down', value: 'Critical Gap', text: 'post-sunset deficit' }}
          badge={<Badge variant={bidSubmitted ? "normal" : "critical"} pulse={!bidSubmitted}>
            {bidSubmitted ? "DAM Booked" : "Action Required"}
          </Badge>}
          icon={AlertTriangle}
          iconBg="bg-rose-100 text-rose-700"
          confidence="93%"
          explain="Solar output ceases while household cooling and commercial peak demand coincide."
        />

        <MetricCard
          title="BESS Storage Absorption"
          value={bessScheduled ? "Scheduled" : "2,400"}
          unit={bessScheduled ? "" : "MWh"}
          subtitle="Midday charging opportunity"
          trend={{ direction: 'up', value: '11:00-14:00', text: 'solar surplus' }}
          badge={<Badge variant={bessScheduled ? "normal" : "warning"}>
            {bessScheduled ? "Charge Queued" : "Surplus Available"}
          </Badge>}
          icon={BatteryCharging}
          iconBg="bg-emerald-100 text-emerald-700"
          confidence="96%"
          explain="Absorb cheap midday solar surplus to discharge during the ₹8.50/kWh evening peak window."
        />

        <MetricCard
          title="Estimated DSM Risk"
          value="₹ 14.2"
          unit="Lakhs"
          subtitle="Deviation settlement penalty exposure"
          trend={{ direction: 'neutral', value: '-65%', text: 'with ML schedule' }}
          badge={<Badge variant="normal">Protected</Badge>}
          icon={ShieldCheck}
          iconBg="bg-teal-100 text-teal-700"
          confidence="94%"
          explain="Precision farm forecasts ensure DISCOM deviations remain within the CERC +/- 150 MW regulatory band."
        />
      </div>

      {/* Hourly Supply vs Demand Balance Table & Actions */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        
        {/* Left: 24h Duck Curve Timeline */}
        <div className="lg:col-span-2 bg-white rounded-2xl border border-slate-200 p-6 shadow-xs">
          <div className="flex items-center justify-between mb-4">
            <div>
              <h2 className="text-base font-bold text-slate-900 flex items-center gap-2">
                <BarChart3 className="w-4 h-4 text-amber-600" />
                Duck Curve & Hourly Deficit / Surplus Ledger
              </h2>
              <p className="text-xs text-slate-500">
                Anticipate shortfall hours to schedule bilateral contracts before market closure
              </p>
            </div>
            <span className="text-[11px] font-semibold text-amber-800 bg-amber-50 px-2.5 py-1 rounded-md border border-amber-200">
              DISCOM Net Load Model
            </span>
          </div>

          <div className="overflow-x-auto">
            <table className="w-full text-left text-xs">
              <thead className="bg-slate-50 text-slate-600 border-b border-slate-200">
                <tr>
                  <th className="py-2.5 px-3 font-bold">Time (IST)</th>
                  <th className="py-2.5 px-3 font-bold">Forecast Demand</th>
                  <th className="py-2.5 px-3 font-bold">Renewable Gen</th>
                  <th className="py-2.5 px-3 font-bold">Net Grid Balance</th>
                  <th className="py-2.5 px-3 font-bold">Operating Directive</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100">
                {hourlyBalance.map((item) => (
                  <tr key={item.hour} className="hover:bg-slate-50/80 transition-colors">
                    <td className="py-3 px-3 font-bold text-slate-800">{item.hour}</td>
                    <td className="py-3 px-3 text-slate-700 font-semibold">{item.demand.toLocaleString()} MW</td>
                    <td className="py-3 px-3 text-emerald-600 font-bold">{item.reGen.toLocaleString()} MW</td>
                    <td className={`py-3 px-3 font-bold ${item.netDemand < 0 ? 'text-emerald-700' : 'text-rose-700'}`}>
                      {item.netDemand > 0 ? `+${item.netDemand.toLocaleString()} MW Deficit` : `${item.netDemand.toLocaleString()} MW Surplus`}
                    </td>
                    <td className="py-3 px-3">
                      <span className={`px-2 py-0.5 rounded text-[11px] font-semibold ${
                        item.status.includes('Surplus')
                          ? 'bg-emerald-50 text-emerald-800 border border-emerald-200'
                          : item.status.includes('Deficit')
                          ? 'bg-rose-50 text-rose-800 border border-rose-200'
                          : 'bg-slate-100 text-slate-700'
                      }`}>
                        {item.status}
                      </span>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>

        {/* Right: Procurement Execution Card */}
        <div className="bg-white rounded-2xl border border-amber-200 p-6 shadow-xs flex flex-col justify-between">
          <div>
            <div className="flex items-center gap-2 text-amber-700 mb-2">
              <Clock className="w-5 h-5" />
              <h3 className="font-bold text-base text-slate-900">Procurement Action Window</h3>
            </div>
            <p className="text-xs text-slate-600 leading-relaxed">
              IEX Day-Ahead Market (DAM) order gate closes at <strong>12:00 IST</strong>. 
              Submitting now ensures clearing at estimated ₹3.90/kWh vs ₹8.50/kWh in the emergency Real-Time Market.
            </p>

            <div className="mt-4 p-3.5 bg-amber-50 rounded-xl border border-amber-200 space-y-2 text-xs text-amber-950">
              <div className="flex justify-between">
                <span className="font-semibold">Recommended DAM Bid:</span>
                <span className="font-bold text-amber-900">3,850 MW (Block 73–88)</span>
              </div>
              <div className="flex justify-between">
                <span className="font-semibold">Est. Savings vs RTM:</span>
                <span className="font-bold text-emerald-700">₹ 1.76 Crore / day</span>
              </div>
              <div className="flex justify-between">
                <span className="font-semibold">BESS Fast Ramp:</span>
                <span>Discharge 1,200 MW @ 18:30 IST</span>
              </div>
            </div>
          </div>

          <div className="mt-6 space-y-2.5 pt-4 border-t border-slate-100">
            <button
              onClick={() => setBidSubmitted(!bidSubmitted)}
              className={`w-full py-2.5 px-4 rounded-xl text-xs font-bold shadow-xs transition-all flex items-center justify-center gap-2 ${
                bidSubmitted
                  ? 'bg-emerald-600 hover:bg-emerald-700 text-white'
                  : 'bg-amber-600 hover:bg-amber-700 text-white'
              }`}
            >
              <ArrowUpRight className="w-4 h-4" />
              <span>{bidSubmitted ? '✓ DAM Schedule Transmitted to IEX' : 'Submit Day-Ahead Bids to Power Exchange'}</span>
            </button>

            <button
              onClick={() => setBessScheduled(!bessScheduled)}
              className="w-full py-2.5 px-4 rounded-xl text-xs font-semibold bg-slate-100 hover:bg-slate-200 text-slate-800 transition-colors flex items-center justify-center gap-2"
            >
              <BatteryCharging className="w-4 h-4 text-emerald-600" />
              <span>{bessScheduled ? '✓ BESS Midday Charging Queued' : 'Queue BESS Absorption (11:00-14:00)'}</span>
            </button>
          </div>
        </div>

      </div>
    </div>
  );
}
