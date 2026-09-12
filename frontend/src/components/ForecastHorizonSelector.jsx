import React from 'react';
import { Clock } from 'lucide-react';

export default function ForecastHorizonSelector({
  value = '24h',
  onChange,
  className = ''
}) {
  const horizons = [
    { id: '24h', label: '24 Hours', sub: 'Day-Ahead Balancing' },
    { id: '48h', label: '48 Hours', sub: 'Short-Term Planning' },
    { id: '72h', label: '72 Hours', sub: 'Multi-Day Dispatch' }
  ];

  return (
    <div className={`inline-flex items-center p-1 bg-slate-100 rounded-xl border border-slate-200/80 ${className}`}>
      {horizons.map((h) => {
        const isSelected = value === h.id;
        return (
          <button
            key={h.id}
            type="button"
            onClick={() => onChange && onChange(h.id)}
            className={`flex items-center gap-2 px-3.5 py-1.5 rounded-lg text-xs font-semibold transition-all duration-150 ${
              isSelected
                ? 'bg-white text-emerald-800 shadow-xs border border-slate-200/80'
                : 'text-slate-600 hover:text-slate-900 hover:bg-slate-200/50'
            }`}
          >
            <Clock className={`w-3.5 h-3.5 ${isSelected ? 'text-emerald-600' : 'text-slate-400'}`} />
            <span>{h.label}</span>
          </button>
        );
      })}
    </div>
  );
}
